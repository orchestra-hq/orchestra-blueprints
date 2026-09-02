# bigquery

A deliberately small dbt Core project for BigQuery: a seed, a typed staging
view, and one mart table. It exists so the demo account has a BigQuery dbt
target that is cheap to build and safe to drop.

- **Profile:** `dbt_bigquery` — the profile name on the Orchestra dbt Core
  connection `dbt_core__bigquery__01406`, not this project's name.
- **Output dataset:** everything lands in `dbt_sao_demo`, pinned by the
  `generate_schema_name` macro so it never inherits the connection's default
  dataset (the prod `core_*` datasets live in the same project).
- **Lineage:** `raw_orders` (seed) → `stg_orders` (view) → `orders_daily` (table).

## Running it

```bash
cd dbt_projects/bigquery
dbt build
```

In Orchestra, point a dbt Core task at `project_dir: dbt_projects/bigquery` with
the connection above.
