#!/usr/bin/env python3
"""Run declarative data quality tests against Snowflake using the DuckDB CLI.

The DuckDB CLI (plus the `snowflake` community extension) is used purely as a
query driver and assertion engine. Every aggregate is evaluated *inside*
Snowflake and only one row per check comes back, so the pattern is safe to
point at billion-row tables.

Checks for a single table are compiled into one SQL statement that scans the
table once, however many checks you declare against it.

Standard library only -- these runtimes frequently have no pip.

Usage:
    ./install_duckdb_snowflake.sh
    python3 run_quality_tests.py --config example.tests.json

Exit codes:
    0  every check passed
    1  at least one check failed or errored (unless --warn-only)
    2  configuration or execution problem
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SECRET_NAME = "dq_secret"

# Snowflake identifiers are interpolated into SQL, so they are whitelisted
# rather than escaped. Quoted / case-sensitive identifiers are not supported.
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")

DEFAULT_CONNECTION_ENV = {
    "account": "SNOWFLAKE_ACCOUNT",
    "user": "SNOWFLAKE_USER",
    "password": "SNOWFLAKE_PASSWORD",
    "database": "SNOWFLAKE_DATABASE",
    "schema": "SNOWFLAKE_SCHEMA",
    "warehouse": "SNOWFLAKE_WAREHOUSE",
    "role": "SNOWFLAKE_ROLE",
}

REQUIRED_CONNECTION_KEYS = ("account", "user", "password")


class ConfigError(Exception):
    """Raised when the test configuration cannot be compiled to SQL."""


# ---------------------------------------------------------------------------
# SQL helpers
# ---------------------------------------------------------------------------

def quote_literal(value) -> str:
    """Render a Python value as a Snowflake SQL literal."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return repr(value)
    return "'" + str(value).replace("'", "''") + "'"


def check_identifier(value: str, what: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER_RE.match(value):
        raise ConfigError(
            f"{what} {value!r} is not a bare Snowflake identifier. "
            "Quoted and case-sensitive identifiers are not supported."
        )
    return value


def check_table(value: str) -> str:
    if not isinstance(value, str):
        raise ConfigError(f"table {value!r} must be a string")
    parts = value.split(".")
    if not 1 <= len(parts) <= 3:
        raise ConfigError(f"table {value!r} must be NAME, SCHEMA.NAME or DB.SCHEMA.NAME")
    for part in parts:
        check_identifier(part, "table part")
    return value


def column_of(check: dict) -> str:
    column = check.get("column")
    if column is None:
        raise ConfigError(f"check {check.get('type')!r} requires a 'column'")
    return check_identifier(column, "column")


def require(check: dict, key: str):
    if key not in check:
        raise ConfigError(f"check {check.get('type')!r} requires {key!r}")
    return check[key]


# ---------------------------------------------------------------------------
# Check compilation
#
# Every single-table check reduces to one aggregate expression plus a
# comparison. Returning (metric_sql, operator, threshold, description) keeps
# the SQL dumb and the pass/fail logic in one auditable place.
# ---------------------------------------------------------------------------

def compile_check(check: dict):
    kind = check.get("type")

    if kind == "row_count_min":
        threshold = require(check, "min")
        return "COUNT(*)", ">=", threshold, f"row count >= {threshold}"

    if kind == "not_null":
        col = column_of(check)
        threshold = check.get("max_null_pct", 0)
        metric = (
            f"100.0 * SUM(CASE WHEN {col} IS NULL THEN 1 ELSE 0 END) "
            "/ NULLIF(COUNT(*), 0)"
        )
        return metric, "<=", threshold, f"{col} null % <= {threshold}"

    if kind == "distinct_floor":
        # Catches flatlined columns: 0% null, fully populated, and stuck on a
        # single value. A null-rate suite reports these as healthy.
        col = column_of(check)
        threshold = check.get("min_distinct", 2)
        return f"COUNT(DISTINCT {col})", ">=", threshold, f"{col} distinct >= {threshold}"

    if kind == "unique":
        col = column_of(check)
        # NULLs are excluded by both COUNT(col) and COUNT(DISTINCT col);
        # pair this with not_null if NULLs matter.
        metric = f"COUNT({col}) - COUNT(DISTINCT {col})"
        return metric, "<=", 0, f"{col} has no duplicates"

    if kind == "freshness":
        # A fully NULL column yields NULL here, which is reported as ERROR
        # rather than quietly skipped -- a dead timestamp column is exactly
        # the failure this check exists to catch.
        col = column_of(check)
        threshold = require(check, "max_age_hours")
        metric = (
            f"DATEDIFF('hour', TO_TIMESTAMP_NTZ(MAX({col})), "
            "CONVERT_TIMEZONE('UTC', CURRENT_TIMESTAMP())::TIMESTAMP_NTZ)"
        )
        return metric, "<=", threshold, f"{col} age (hours) <= {threshold}"

    if kind == "accepted_range":
        col = column_of(check)
        low, high = require(check, "min"), require(check, "max")
        metric = (
            f"SUM(CASE WHEN {col} < {quote_literal(low)} "
            f"OR {col} > {quote_literal(high)} THEN 1 ELSE 0 END)"
        )
        return metric, "<=", check.get("max_violations", 0), f"{col} within [{low}, {high}]"

    if kind == "accepted_values":
        col = column_of(check)
        values = require(check, "values")
        if not isinstance(values, list) or not values:
            raise ConfigError("accepted_values requires a non-empty 'values' list")
        rendered = ", ".join(quote_literal(v) for v in values)
        metric = (
            f"SUM(CASE WHEN {col} IS NOT NULL AND {col} NOT IN ({rendered}) "
            "THEN 1 ELSE 0 END)"
        )
        return metric, "<=", check.get("max_violations", 0), f"{col} in accepted values"

    raise ConfigError(f"unknown single-table check type {kind!r}")


def compile_standalone(check: dict, table: str):
    """Checks that need their own query because they cannot share a table scan."""
    kind = check.get("type")

    if kind == "no_orphans":
        col = column_of(check)
        ref_table = check_table(require(check, "ref_table"))
        ref_column = check_identifier(require(check, "ref_column"), "ref_column")
        sql = (
            f"SELECT COUNT(*) AS observed FROM {table} c "
            f"LEFT JOIN {ref_table} p ON c.{col} = p.{ref_column} "
            f"WHERE c.{col} IS NOT NULL AND p.{ref_column} IS NULL"
        )
        desc = f"{col} has no orphans against {ref_table}.{ref_column}"
        return sql, "<=", check.get("max_violations", 0), desc

    if kind == "custom_sql":
        sql = require(check, "sql")
        if not isinstance(sql, str) or ";" in sql:
            raise ConfigError("custom_sql must be a single statement with no semicolon")
        operator = check.get("operator", "<=")
        if operator not in ("<=", ">=", "==", "<", ">"):
            raise ConfigError(f"unsupported operator {operator!r}")
        threshold = require(check, "threshold")
        desc = check.get("description", f"custom_sql {operator} {threshold}")
        return f"SELECT ({sql}) AS observed", operator, threshold, desc

    return None


STANDALONE_TYPES = {"no_orphans", "custom_sql"}


def build_units(config: dict):
    """Compile the config into (unit_id, snowflake_sql, [check metadata]) tuples."""
    suites = config.get("suites")
    if not isinstance(suites, list) or not suites:
        raise ConfigError("config needs a non-empty 'suites' list")

    units = []
    for suite_idx, suite in enumerate(suites):
        table = check_table(require(suite, "table"))
        criticality = suite.get("criticality", "unspecified")
        checks = suite.get("checks") or []
        if not checks:
            raise ConfigError(f"suite {table} has no checks")

        inline, aggregates = [], []
        for check in checks:
            common = {
                "table": table,
                "criticality": criticality,
                "type": check.get("type"),
                "column": check.get("column"),
                "severity": check.get("severity", "unspecified"),
            }

            standalone = compile_standalone(check, table)
            if standalone is not None:
                sql, operator, threshold, desc = standalone
                units.append((
                    f"s{suite_idx}_x{len(units)}",
                    sql,
                    [dict(common, operator=operator, threshold=threshold, description=desc)],
                ))
                continue

            metric, operator, threshold, desc = compile_check(check)
            alias = f"m{len(inline)}"
            aggregates.append(f"{metric} AS {alias}")
            inline.append(
                dict(common, operator=operator, threshold=threshold,
                     description=desc, alias=alias)
            )

        if inline:
            # One scan of the table, however many checks are declared.
            agg = f"WITH agg AS (SELECT {', '.join(aggregates)} FROM {table})"
            rows = " UNION ALL ".join(
                f"SELECT {idx} AS check_idx, CAST({meta['alias']} AS DOUBLE) AS observed FROM agg"
                for idx, meta in enumerate(inline)
            )
            units.append((f"s{suite_idx}_agg", f"{agg} {rows}", inline))

    return units


# ---------------------------------------------------------------------------
# DuckDB execution
# ---------------------------------------------------------------------------

def build_secret_sql(config: dict) -> str:
    env_map = dict(DEFAULT_CONNECTION_ENV)
    env_map.update(config.get("connection_env", {}))

    fields = []
    for key, var in env_map.items():
        if not var:
            continue
        if key in REQUIRED_CONNECTION_KEYS and not os.environ.get(var):
            raise ConfigError(f"required environment variable {var} is not set")
        if os.environ.get(var):
            # getenv() keeps credentials out of the generated SQL entirely --
            # nothing sensitive is written to disk or passed on argv.
            fields.append(f"{key.upper()} getenv({quote_literal(var)})")

    return (
        f"CREATE OR REPLACE SECRET {SECRET_NAME} "
        f"(TYPE snowflake, {', '.join(fields)});"
    )


def run_duckdb(duckdb_bin: str, config: dict, units, workdir: Path):
    statements = ["LOAD snowflake;", build_secret_sql(config)]
    outputs = {}

    for unit_id, sql, _ in units:
        out_path = workdir / f"{unit_id}.json"
        outputs[unit_id] = out_path
        inner = sql.replace("'", "''")
        statements.append(
            f"COPY (SELECT * FROM snowflake_query('{inner}', '{SECRET_NAME}')) "
            f"TO {quote_literal(str(out_path))} (FORMAT JSON, ARRAY true);"
        )

    script = "\n".join(statements) + "\n"
    proc = subprocess.run(
        [duckdb_bin, "-init", "/dev/null", "-batch"],
        input=script,
        capture_output=True,
        text=True,
    )
    return outputs, proc


def evaluate(observed, operator: str, threshold) -> str:
    if observed is None:
        return "ERROR"
    try:
        observed = float(observed)
        threshold = float(threshold)
    except (TypeError, ValueError):
        return "ERROR"
    comparisons = {
        "<=": observed <= threshold,
        ">=": observed >= threshold,
        "<": observed < threshold,
        ">": observed > threshold,
        "==": observed == threshold,
    }
    return "PASS" if comparisons[operator] else "FAIL"


def collect_results(units, outputs, proc):
    results = []
    for unit_id, _, metas in units:
        path = outputs[unit_id]
        if not path.exists():
            # Whole unit failed -- surface it as one errored row per check
            # rather than silently reporting fewer checks than were declared.
            lines = [l.strip() for l in
                     (proc.stderr or proc.stdout or "").splitlines() if l.strip()]
            # DuckDB prints a caret-underline after the message; pick the
            # message itself rather than whatever happened to be printed last.
            errors = [l for l in lines if "error" in l.lower()]
            reason = (errors or lines or ["query did not run"])[0][:300]
            for meta in metas:
                results.append(dict(meta, observed=None, status="ERROR", error=reason))
            continue

        # Snowflake returns unquoted aliases upper-cased, so match on
        # case-folded keys rather than assuming either casing.
        rows = [
            {str(k).lower(): v for k, v in row.items()}
            for row in json.loads(path.read_text() or "[]")
        ]
        if len(metas) == 1 and "check_idx" not in (rows[0] if rows else {}):
            by_idx = {0: (rows[0].get("observed") if rows else None)}
        else:
            by_idx = {int(r["check_idx"]): r.get("observed") for r in rows}

        for idx, meta in enumerate(metas):
            observed = by_idx.get(idx)
            status = evaluate(observed, meta["operator"], meta["threshold"])
            entry = dict(meta, observed=observed, status=status)
            if status == "ERROR":
                entry["error"] = "metric returned NULL (column may be empty or absent)"
            entry.pop("alias", None)
            results.append(entry)
    return results


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_report(results) -> None:
    width = max([len(r["table"]) for r in results] + [5])
    icons = {"PASS": "PASS ", "FAIL": "FAIL ", "ERROR": "ERROR"}
    print()
    print(f"{'STATUS':6} {'TABLE':{width}}  {'CHECK':38} {'OBSERVED':>12}  THRESHOLD")
    print("-" * (width + 78))
    order = {"ERROR": 0, "FAIL": 1, "PASS": 2}
    for r in sorted(results, key=lambda r: (order[r["status"]], r["table"])):
        observed = "-" if r["observed"] is None else f"{float(r['observed']):.4g}"
        print(
            f"{icons[r['status']]:6} {r['table']:{width}}  "
            f"{r['description'][:38]:38} {observed:>12}  "
            f"{r['operator']} {r['threshold']}"
        )
        if r.get("error"):
            print(f"{'':6} {'':{width}}  -> {r['error']}")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="example.tests.json")
    parser.add_argument(
        "--duckdb",
        default=os.environ.get("DUCKDB_BIN", str(Path.home() / ".local/duckdb/duckdb")),
        help="Path to the DuckDB CLI installed by install_duckdb_snowflake.sh",
    )
    parser.add_argument("--output", help="Write machine-readable JSON results here")
    parser.add_argument("--warn-only", action="store_true",
                        help="Always exit 0, even when checks fail")
    args = parser.parse_args()

    if not Path(args.duckdb).exists():
        print(f"DuckDB CLI not found at {args.duckdb}. "
              "Run ./install_duckdb_snowflake.sh first.", file=sys.stderr)
        return 2

    try:
        config = json.loads(Path(args.config).read_text())
        units = build_units(config)
    except (OSError, json.JSONDecodeError, ConfigError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory() as tmp:
        try:
            outputs, proc = run_duckdb(args.duckdb, config, units, Path(tmp))
        except ConfigError as exc:
            print(f"Configuration error: {exc}", file=sys.stderr)
            return 2
        results = collect_results(units, outputs, proc)

    if all(r["status"] == "ERROR" for r in results) and results:
        print("Every check errored -- the connection itself is probably broken.",
              file=sys.stderr)
        print((proc.stderr or proc.stdout or "").strip()[-2000:], file=sys.stderr)

    print_report(results)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(results),
        "passed": sum(r["status"] == "PASS" for r in results),
        "failed": sum(r["status"] == "FAIL" for r in results),
        "errored": sum(r["status"] == "ERROR" for r in results),
    }
    print("  ".join(f"{k}={v}" for k, v in summary.items() if k != "generated_at"))

    if args.output:
        Path(args.output).write_text(
            json.dumps({"summary": summary, "results": results}, indent=2, default=str)
        )
        print(f"JSON results written to {args.output}")

    if args.warn_only:
        return 0
    return 1 if summary["failed"] or summary["errored"] else 0


if __name__ == "__main__":
    sys.exit(main())
