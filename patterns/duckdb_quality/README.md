# DuckDB Data Quality Tests on Snowflake

Run declarative data quality tests against Snowflake using the **DuckDB CLI** as
the query driver and assertion engine, in runtimes where you have no root, no
`pip`, and no `unzip` — Orchestra agent sandboxes, slim CI images, locked-down
containers.

> **DuckDB is not the compute here.** Every aggregate is evaluated *inside*
> Snowflake via the `snowflake` community extension and only one row per check
> comes back. DuckDB compiles the tests, applies the thresholds, and formats
> the report. Do not use this pattern to pull tables down and test them
> locally — the tables this is aimed at have hundreds of millions of rows.

## Files

| File | Purpose |
| --- | --- |
| `install_duckdb_snowflake.sh` | Installs the DuckDB CLI, the `snowflake` extension, and the ADBC driver. No root, no pip, no unzip. |
| `run_quality_tests.py` | Compiles `tests.json` into pushed-down SQL, runs it, reports results. Standard library only. |
| `example.tests.json` | Example test suite to copy and edit. |
| `.env.example` | Credential variable names. |

## Usage

```bash
./install_duckdb_snowflake.sh              # prints the CLI path; idempotent
export SNOWFLAKE_ACCOUNT=... SNOWFLAKE_USER=... SNOWFLAKE_PASSWORD=...
python3 run_quality_tests.py --config example.tests.json --output results.json
```

Exit codes: `0` all passed, `1` something failed or errored, `2` bad config or
the run could not execute. Use `--warn-only` to always exit `0` while you are
building a suite up.

Real output, against a table in a test account:

```
STATUS TABLE                                                  CHECK                                      OBSERVED  THRESHOLD
-----------------------------------------------------------------------------------------------------------------------------
ERROR  SNOWFLAKE_WORKING.PUBLIC_CLEAN.SNOWFLAKE_ORDERS_CLEAN  SOLD_DATE age (hours) <= 48                       -  <= 48
       -> metric returned NULL (column may be empty or absent)
FAIL   SNOWFLAKE_WORKING.PUBLIC_CLEAN.SNOWFLAKE_ORDERS_CLEAN  SOLD_DATE null % <= 5                           100  <= 5
FAIL   SNOWFLAKE_WORKING.PUBLIC_CLEAN.SNOWFLAKE_ORDERS_CLEAN  BILL_CUTOMER_SK_ID null % <= 5                 24.1  <= 5
FAIL   SNOWFLAKE_WORKING.PUBLIC_CLEAN.SNOWFLAKE_ORDERS_CLEAN  ITEM_SK_ID distinct >= 2                          1  >= 2
PASS   SNOWFLAKE_WORKING.PUBLIC_CLEAN.SNOWFLAKE_ORDERS_CLEAN  row count >= 1                                 1000  >= 1
PASS   SNOWFLAKE_WORKING.PUBLIC_CLEAN.SNOWFLAKE_ORDERS_CLEAN  ORDER_NUMBER has no duplicates                    0  <= 0

total=9  passed=5  failed=3  errored=1
```

## Check types

All single-table checks declared against one table are compiled into a
**single statement that scans that table once**, however many you declare.

| Type | Required keys | Passes when |
| --- | --- | --- |
| `row_count_min` | `min` | row count >= `min` |
| `not_null` | `column`, `max_null_pct` | null percentage <= `max_null_pct` |
| `distinct_floor` | `column`, `min_distinct` | distinct values >= `min_distinct` |
| `unique` | `column` | no duplicate non-null values |
| `freshness` | `column`, `max_age_hours` | `MAX(column)` is within `max_age_hours` |
| `accepted_range` | `column`, `min`, `max` | no values outside the range |
| `accepted_values` | `column`, `values` | no non-null values outside the list |
| `no_orphans` | `column`, `ref_table`, `ref_column` | no non-null values missing from the parent |
| `custom_sql` | `sql`, `operator`, `threshold` | scalar result satisfies the comparison |

`no_orphans` and `custom_sql` each need their own query — they cannot share a
table scan. Every check also accepts an optional `severity`, and every suite an
optional `criticality`; both are passed straight through to the JSON output so
downstream triage can rank findings without re-deriving them.

```json
{
  "type": "no_orphans",
  "column": "BILL_CUTOMER_SK_ID",
  "ref_table": "SNOWFLAKE_WORKING.PUBLIC.CUSTOMERS",
  "ref_column": "CUSTOMER_SK_ID",
  "severity": "high"
}
```

## Include `distinct_floor` and `freshness`, not just null checks

The two most expensive failures in practice are invisible to a null-rate suite:

- **Flatlined columns.** A column that is 0% null, fully populated, and stuck
  on a single value passes every completeness check. `distinct_floor` is what
  catches it. In the run above, `ITEM_SK_ID` had exactly one distinct value
  across every row.
- **Dead timestamps.** A 100% NULL date column makes `MAX()` return NULL. This
  runner reports that as `ERROR`, not as a skip — "we could not evaluate
  freshness" is a data quality finding, not an absence of one.

Both shapes generate downstream anomaly alerts that look like operational
incidents and are not. Catching them here is what removes that noise.

## Why the installer is the length it is

Each of these is a real failure mode that costs an afternoon:

| Trap | What happens |
| --- | --- |
| Assuming x86_64 | The `linux-amd64` zip downloads and extracts happily on arm64, then dies with `Exec format error`. The script reads `uname -m`. |
| No `unzip` | Not present in slim images. The script extracts with `python3 -m zipfile`. |
| No `pip` | The `snowflake` extension is an ADBC wrapper and is useless without `libadbc_driver_snowflake`. There is no standalone tarball, so the script pulls the PyPI wheel with `curl` and opens it as a zip. |
| Version-stamped driver path | DuckDB looks for the driver under `~/.duckdb/extensions/<version>/<platform>/`. Installing "latest" against a hardcoded path breaks silently on the next DuckDB release; the script asks the binary for `version()` and `pragma platform`. |
| Missing `READ_ONLY` | `ATTACH` without it fails: *Snowflake currently only supports read-only access*. This runner uses `snowflake_query()` and avoids `ATTACH` entirely. |
| Argument order | It is `snowflake_query('<sql>', '<secret>')`. Reversed, the error is a "profile not found" message with your whole query pasted into it. |

## Credentials

Credentials are read with DuckDB's `getenv()` inside the generated SQL, so no
secret is written into a `.sql` file, onto disk, or onto a command line where
`ps` could see it. Set the variables in `.env.example`, or point at different
names with the `connection_env` block in the config:

```json
"connection_env": { "password": "MY_OTHER_PASSWORD_VAR" }
```

`account`, `user` and `password` are required; the rest are sent only if set.

## Limitations

- **Bare identifiers only.** Table and column names are whitelisted against
  `^[A-Za-z_][A-Za-z0-9_$]*$` because they are interpolated into SQL. Quoted,
  lower-case or case-sensitive identifiers are not supported.
- **`custom_sql` is not validated.** It is your SQL, run as-is under your role.
  Anyone who can edit the config can run arbitrary read queries.
- **`unique` ignores NULLs**, as `COUNT(DISTINCT ...)` does. Pair it with
  `not_null` when NULLs matter.
- **`freshness` assumes UTC-stored timestamps.** It compares against
  `CONVERT_TIMEZONE('UTC', CURRENT_TIMESTAMP())`.
- **Each suite is one warehouse query** (plus one per `no_orphans` /
  `custom_sql`). Grouping checks by table is what keeps warehouse cost down.
- **Ephemeral home directories.** In sandboxes that reset between sessions the
  installer re-downloads roughly 80 MB every time.
- Tested on DuckDB v1.5.6, `snowflake` community extension `b61f5ad`, ADBC
  driver 1.11.0, Linux arm64, username/password auth. Key-pair and SSO auth are
  not wired up.
