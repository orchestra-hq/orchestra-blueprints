"""Task 2 — consume the source catalogue that arrives purely as env vars.

This script knows nothing about the Orchestra SDK's outputs API and never calls
back to fetch anything. It just reads environment variables:

    SOURCE_MANIFEST       JSON string produced by set_sources.py
    ACTIVE_SOURCE_NAMES   comma-separated names, used as a cross-check
    ACTIVE_SOURCE_COUNT   integer as a string, used as a cross-check

The pipeline wires those in from the upstream task's outputs, so locally you can
run the same script with:

    SOURCE_MANIFEST='{"sources": [...]}' python process_sources.py

"Does something else with them": builds the per-source load plan — the MERGE or
CREATE OR REPLACE SQL each source needs, plus its freshness check — and prints
it. Swap the print for a warehouse execute and this is a real loader.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone

TARGET_DATABASE = os.environ.get("TARGET_DATABASE", "ANALYTICS")
TARGET_SCHEMA = os.environ.get("TARGET_SCHEMA", "STAGING")
DRY_RUN = os.environ.get("DRY_RUN", "true").lower() in {"1", "true", "yes"}


class MissingEnvironment(RuntimeError):
    pass


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        raise MissingEnvironment(
            f"{name} is empty. It should be injected by the pipeline from the "
            f"upstream task's outputs — check the task's environment_variables "
            f"block and that the upstream task has set_outputs enabled."
        )
    return value


def load_manifest() -> dict:
    raw = require_env("SOURCE_MANIFEST")
    try:
        manifest = json.loads(raw)
    except json.JSONDecodeError as e:
        raise MissingEnvironment(
            f"SOURCE_MANIFEST is not valid JSON ({e}). First 200 chars: {raw[:200]!r}"
        ) from e

    if not isinstance(manifest, dict) or "sources" not in manifest:
        raise MissingEnvironment(
            f"SOURCE_MANIFEST must be an object with a 'sources' key, got {type(manifest).__name__}"
        )
    return manifest


def cross_check(manifest: dict) -> None:
    """The two scalar env vars exist so a truncated manifest is caught early."""
    sources = manifest["sources"]

    expected_count = os.environ.get("ACTIVE_SOURCE_COUNT")
    if expected_count and int(expected_count) != len(sources):
        raise MissingEnvironment(
            f"ACTIVE_SOURCE_COUNT says {expected_count} but the manifest has "
            f"{len(sources)} sources — the manifest was probably truncated."
        )

    expected_names = os.environ.get("ACTIVE_SOURCE_NAMES")
    if expected_names:
        want = {n.strip() for n in expected_names.split(",") if n.strip()}
        got = {s["name"] for s in sources}
        if want != got:
            raise MissingEnvironment(
                f"name mismatch. only in ACTIVE_SOURCE_NAMES: {sorted(want - got)}, "
                f"only in manifest: {sorted(got - want)}"
            )


def fully_qualified(source: dict) -> str:
    return f"{source['database']}.{source['schema']}.{source['table']}"


def target_table(source: dict) -> str:
    return f"{TARGET_DATABASE}.{TARGET_SCHEMA}.STG_{source['name'].upper()}"


def build_sql(source: dict) -> str:
    src = fully_qualified(source)
    tgt = target_table(source)

    if source["load_strategy"] == "incremental":
        cursor = source["cursor_field"]
        return (
            f"MERGE INTO {tgt} AS t\n"
            f"USING (\n"
            f"    SELECT * FROM {src}\n"
            f"    WHERE {cursor} > COALESCE(\n"
            f"        (SELECT MAX({cursor}) FROM {tgt}), '1900-01-01'::timestamp_ntz\n"
            f"    )\n"
            f") AS s\n"
            f"ON t.ID = s.ID\n"
            f"WHEN MATCHED THEN UPDATE SET *\n"
            f"WHEN NOT MATCHED THEN INSERT *;"
        )

    return f"CREATE OR REPLACE TABLE {tgt} AS\nSELECT * FROM {src};"


def build_freshness_check(source: dict) -> str | None:
    cursor = source.get("cursor_field")
    if not cursor:
        return None

    deadline = datetime.now(timezone.utc) - timedelta(hours=source["freshness_sla_hours"])
    return (
        f"SELECT '{source['name']}' AS source, MAX({cursor}) AS last_loaded\n"
        f"FROM {fully_qualified(source)}\n"
        f"HAVING MAX({cursor}) < '{deadline.strftime('%Y-%m-%d %H:%M:%S')}'::timestamp_ntz;"
    )


def main() -> int:
    try:
        manifest = load_manifest()
        cross_check(manifest)
    except MissingEnvironment as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    sources = manifest["sources"]
    print(f"Manifest generated at : {manifest.get('generated_at', 'unknown')}")
    print(f"Upstream pipeline run : {manifest.get('pipeline_run_id', 'unknown')}")
    print(f"Target                : {TARGET_DATABASE}.{TARGET_SCHEMA}")
    print(f"Mode                  : {'DRY RUN' if DRY_RUN else 'EXECUTE'}")
    print(f"Sources               : {len(sources)}\n")

    incremental = sum(1 for s in sources if s["load_strategy"] == "incremental")
    checks = 0

    for source in sources:
        print("=" * 72)
        print(f"{source['name']}  ({source['connector']} -> {target_table(source)})")
        print("=" * 72)
        print(build_sql(source))

        freshness = build_freshness_check(source)
        if freshness:
            checks += 1
            print(f"\n-- freshness check ({source['freshness_sla_hours']}h SLA)")
            print(freshness)
        print()

        if not DRY_RUN:
            # Replace with your warehouse client, e.g.
            #   snowflake.connector.connect(...).cursor().execute(sql)
            print(f"[execute] would run {len(build_sql(source).splitlines())} lines "
                  f"against {target_table(source)}")

    print(
        f"Plan complete: {len(sources)} sources "
        f"({incremental} incremental, {len(sources) - incremental} full refresh), "
        f"{checks} freshness checks."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
