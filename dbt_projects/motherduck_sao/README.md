# motherduck_sao

A deliberately small dbt Core project for MotherDuck, mirroring
[`dbt_projects/bigquery`](../bigquery): a source, a typed staging view, and one
mart table. It exists so the demo account has a MotherDuck dbt target that is
cheap to build and safe to drop.

- **Profile:** `motherduck` — the profile name that must be defined in the
  `profiles.yml` on the Orchestra dbt Core connection, not this project's name.
- **Output schema:** everything lands in `dbt_sao_demo`, pinned by the
  `generate_schema_name` macro so it never inherits the connection's default
  schema.
- **Lineage:** `raw.raw_orders` (source) → `stg_orders` (view) → `orders_daily`
  (table).
- **Mid-DAG model:** `stg_orders` — the relation
  [`orchestra/dbt/sao_multi_warehouse.yml`](../../orchestra/dbt/sao_multi_warehouse.yml)
  drops and then queries to exercise state-aware orchestration's reuse path.

## The source

`my_db.dbt_sao_demo.raw_orders` is a standing table this project
reads but does not own. It carries an explicit `loaded_at_field`, because
without one everything downstream of the source rebuilds on every run.

The pipeline's `seed raw_orders` step creates it and resets its rows, so there
is nothing to run by hand. The equivalent DDL, for a local build or a manual
reset:

```sql
CREATE SCHEMA IF NOT EXISTS my_db.dbt_sao_demo;

CREATE OR REPLACE TABLE my_db.dbt_sao_demo.raw_orders AS
SELECT *
FROM (VALUES
  (1, 101, DATE '2026-08-01', 'completed', 120.50),
  (2, 102, DATE '2026-08-01', 'completed', 75.00),
  (3, 101, DATE '2026-08-02', 'returned', 120.50),
  (4, 103, DATE '2026-08-02', 'completed', 240.00),
  (5, 104, DATE '2026-08-03', 'pending', 18.99),
  (6, 102, DATE '2026-08-03', 'completed', 64.25),
  (7, 105, DATE '2026-08-04', 'completed', 310.10),
  (8, 103, DATE '2026-08-04', 'pending', 45.00)
) AS t(order_id, customer_id, order_date, status, amount);
```

## MotherDuck specifics

The pins match `motherduck_s3` and `motherduck_oil` — `duckdb==1.5.2` with
`dbt-duckdb==1.10.1` — because those are the versions this account's MotherDuck
instance is known to work with, and because they install from prebuilt wheels.
Do **not** use `dbt-duckdb[md]`: the `md` extra pins `duckdb==1.5.5`, which has
no wheel for the aarch64 runtime Orchestra's dbt Core task uses, so pip falls
back to building DuckDB from source and the task sits in "Installing Python
dependencies" for tens of minutes.

The database is `my_db`, so relations are three-part
(`my_db.dbt_sao_demo.stg_orders`) in the pipeline's drop and query steps.

## Running it

```bash
cd dbt_projects/motherduck_sao
dbt build
```

In Orchestra, point a dbt Core task at `project_dir: dbt_projects/motherduck_sao`.
A matching `profiles.yml` for the connection looks like:

```yaml
motherduck:
  target: prod
  outputs:
    prod:
      type: duckdb
      path: 'md:my_db'
      schema: dbt_sao_demo
      threads: 4
      settings:
        motherduck_token: "{{ env_var('MOTHERDUCK_TOKEN') }}"
```
