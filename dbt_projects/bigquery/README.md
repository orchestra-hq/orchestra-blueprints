# bigquery

A deliberately small dbt Core project for BigQuery: a source, a typed staging
view, and one mart table. It exists so the demo account has a BigQuery dbt
target that is cheap to build and safe to drop.

- **Profile:** `dbt_bigquery` — the profile name on the Orchestra dbt Core
  connection `dbt_core__bigquery__01406`, not this project's name.
- **Output dataset:** everything lands in `dbt_sao_demo`, pinned by the
  `generate_schema_name` macro so it never inherits the connection's default
  dataset (the prod `core_*` datasets live in the same project).
- **Lineage:** `raw.raw_orders` (source) → `Stg Orders Clean` (view) →
  `orders_daily` (table). The staging model is still named `stg_orders` in dbt;
  only its `alias` carries the awkward relation name, which BigQuery permits
  because table names may contain Unicode `Zs` spaces and are case-sensitive.

## The source

`dbt_sao_demo.raw_orders` is a standing table this project reads but does not
own — it was originally loaded by a dbt seed, which has since been removed. It
carries an explicit `loaded_at_field`, because BigQuery has no implicit
freshness fallback in state-aware orchestration: without it, everything
downstream of the source rebuilds on every run.

If the dataset is ever wiped, recreate the table with:

```sql
CREATE OR REPLACE TABLE `dbt_sao_demo.raw_orders` AS
SELECT * FROM UNNEST([
  STRUCT(1 AS order_id, 101 AS customer_id, DATE '2026-08-01' AS order_date, 'completed' AS status, NUMERIC '120.50' AS amount),
  (2, 102, DATE '2026-08-01', 'completed', NUMERIC '75.00'),
  (3, 101, DATE '2026-08-02', 'returned',  NUMERIC '120.50'),
  (4, 103, DATE '2026-08-02', 'completed', NUMERIC '240.00'),
  (5, 104, DATE '2026-08-03', 'pending',   NUMERIC '18.99'),
  (6, 102, DATE '2026-08-03', 'completed', NUMERIC '64.25'),
  (7, 105, DATE '2026-08-04', 'completed', NUMERIC '310.10'),
  (8, 103, DATE '2026-08-04', 'pending',   NUMERIC '45.00')
]);
```

## Running it

```bash
cd dbt_projects/bigquery
dbt build
```

In Orchestra, point a dbt Core task at `project_dir: dbt_projects/bigquery` with
the connection above; [`orchestra/dbt/sao_multi_warehouse.yml`](../../orchestra/dbt/sao_multi_warehouse.yml)
is the pipeline that does.
