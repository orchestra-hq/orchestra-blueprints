# Reusable mart SQL patterns

DuckDB-flavoured. Drop-in for `CREATE OR REPLACE TABLE <db>.<marts_schema>.<x> AS …`.

## Status-split fact

```sql
CREATE OR REPLACE TABLE <db>.<marts_schema>.fct_daily_<entity>_health AS
SELECT
  DATE_TRUNC('day', started_at) AS run_date,
  <entity>_id,
  <entity>_name,
  env_name,
  COUNT(*) AS total_runs,
  COUNT(*) FILTER (WHERE run_status = 'SUCCEEDED') AS succeeded_runs,
  COUNT(*) FILTER (WHERE run_status = 'FAILED')    AS failed_runs,
  COUNT(*) FILTER (WHERE run_status = 'WARNING')   AS warning_runs,
  COUNT(*) FILTER (WHERE run_status = 'CANCELLED') AS cancelled_runs,
  ROUND(100.0 * COUNT(*) FILTER (WHERE run_status = 'SUCCEEDED') / NULLIF(COUNT(*), 0), 2) AS success_rate_pct
FROM <db>.<marts_schema>.fct_<entity>_run
GROUP BY ALL;
```

Notes:
- Filter on `run_status` *before* `UPPER()`-ing if you trust the source; the
  Dive layer can normalise. If the source is dirty, normalise here:
  `UPPER(run_status) IN ('FAILED','ERROR')`.
- `NULLIF(COUNT(*), 0)` keeps the percentage non-fatal on empty days.

## DLT child-table flattening

Source has `assets`, `assets__owners`, `assets__upstream_dependencies`,
`assets__downstream_dependencies`. The owner / dependency rows are list
elements with `_dlt_parent_id` pointing to `assets._dlt_id`.

```sql
CREATE OR REPLACE TABLE <db>.<marts_schema>.dim_asset AS
WITH owner_agg AS (
  SELECT
    _dlt_parent_id AS asset_row_id,
    STRING_AGG(value, ', ' ORDER BY _dlt_list_idx) AS owners
  FROM <db>.<source_schema>.assets__owners
  GROUP BY 1
),
upstream_agg AS (
  SELECT _dlt_parent_id AS asset_row_id, COUNT(*) AS upstream_dependency_count
  FROM <db>.<source_schema>.assets__upstream_dependencies
  GROUP BY 1
),
downstream_agg AS (
  SELECT _dlt_parent_id AS asset_row_id, COUNT(*) AS downstream_dependency_count
  FROM <db>.<source_schema>.assets__downstream_dependencies
  GROUP BY 1
)
SELECT
  a.asset_id,
  a.asset_name,
  a.asset_type,
  …
  oa.owners,
  COALESCE(ua.upstream_dependency_count, 0)   AS upstream_dependency_count,
  COALESCE(da.downstream_dependency_count, 0) AS downstream_dependency_count
FROM <db>.<source_schema>.assets a
LEFT JOIN owner_agg      oa ON a._dlt_id = oa.asset_row_id
LEFT JOIN upstream_agg   ua ON a._dlt_id = ua.asset_row_id
LEFT JOIN downstream_agg da ON a._dlt_id = da.asset_row_id;
```

The `COALESCE(.., 0)` is important — assets with no dependencies don't appear
in the child table at all.

## Duration in seconds

```sql
DATEDIFF('second', started_at, completed_at) AS duration_seconds
```

Use this in any `fct_*_run` table. Beats `EXTRACT(EPOCH FROM …)` for clarity.

## Dim from a fact (entity rollup)

When there's no first-class entity table, derive the dim from the fact:

```sql
CREATE OR REPLACE TABLE <db>.<marts_schema>.dim_<entity> AS
SELECT
  <entity>_id,
  <entity>_name,
  env_id,
  env_name,
  MIN(created_at) AS first_seen_at,
  MAX(updated_at) AS last_seen_at,
  COUNT(*) AS total_runs
FROM <db>.<source_schema>.<entity>_runs
GROUP BY ALL;
```

`GROUP BY ALL` here groups by `<entity>_id`, `<entity>_name`, `env_id`,
`env_name` — the four non-aggregated columns. Make sure that combination is
actually the dim's grain; otherwise you'll get duplicates from a renamed
entity over time.

## Anti-patterns

- **Don't** mix `MD_CREATE_DIVE` into the marts pipeline. Step 2 owns Dive
  publishing. Keep marts deterministic.
- **Don't** put SELECT-only queries in `parameters.query` and rely on the
  result — Orchestra tasks need `set_outputs: true` to expose rows, and even
  then the consumer needs to read them by ID. For marts, always `CREATE OR
  REPLACE TABLE …`.
- **Don't** parametrise mart SQL with `${{ inputs.x }}` inside the query
  string. It won't substitute. Hardcode and rebuild the YAML if you need to
  change a value.
