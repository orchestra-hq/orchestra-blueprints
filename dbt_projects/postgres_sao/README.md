# postgres_sao

A deliberately small dbt Core project for Postgres, mirroring
[`dbt_projects/bigquery`](../bigquery): a source, a typed staging view, and one
mart table. It exists so the demo account has a Postgres dbt target that is
cheap to build and safe to drop.

- **Profile:** `dbt_postgres` — the profile name that must be defined in the
  `profiles.yml` on the Orchestra dbt Core connection, not this project's name.
- **Output schema:** everything lands in `dbt_sao_demo`, pinned by the
  `generate_schema_name` macro so it never inherits the connection's default
  schema.
- **Lineage:** `raw.raw_orders` (source) → `Stg Orders Clean` (view) → `orders_daily`
  (table). The staging model is still named `stg_orders` in dbt; only its
  `alias` carries the awkward relation name.
- **Mid-DAG model:** `dbt_sao_demo."Stg Orders Clean"` — the relation
  [`orchestra/dbt/sao_multi_warehouse.yml`](../../orchestra/dbt/sao_multi_warehouse.yml)
  drops and then queries to exercise state-aware orchestration's reuse path.

## The source

`dbt_sao_demo.raw_orders` is a standing table this project
reads but does not own. It carries an explicit `loaded_at_field`, because
without one everything downstream of the source rebuilds on every run.

The pipeline's `seed raw_orders` step creates it and resets its rows, so there
is nothing to run by hand. The equivalent DDL, for a local build or a manual
reset:

```sql
CREATE SCHEMA IF NOT EXISTS dbt_sao_demo;

DROP TABLE IF EXISTS dbt_sao_demo.raw_orders;
CREATE TABLE dbt_sao_demo.raw_orders (
    order_id    integer,
    customer_id integer,
    order_date  date,
    status      text,
    amount      numeric(10, 2)
);

INSERT INTO dbt_sao_demo.raw_orders VALUES
  (1, 101, '2026-08-01', 'completed', 120.50),
  (2, 102, '2026-08-01', 'completed', 75.00),
  (3, 101, '2026-08-02', 'returned', 120.50),
  (4, 103, '2026-08-02', 'completed', 240.00),
  (5, 104, '2026-08-03', 'pending', 18.99),
  (6, 102, '2026-08-03', 'completed', 64.25),
  (7, 105, '2026-08-04', 'completed', 310.10),
  (8, 103, '2026-08-04', 'pending', 45.00);
```

## Postgres specifics

`count(*) filter (where ...)` is Postgres-native; the Redshift twin of this
project spells the same thing as a `sum(case when ...)` because Redshift has no
`FILTER` clause.

## The awkward relation name

`stg_orders` is aliased to `Stg Orders Clean`, so the relation the pipeline drops and
queries needs quoting to resolve at all. That is deliberate: it makes the lane a
test of whether state-aware orchestration resolves a non-trivial identifier, not
just a well-behaved one.

Postgres keeps the case of a double-quoted identifier and compares it case-sensitively, so the name exercises both quoting and case.

Aliasing rather than renaming keeps `ref('stg_orders')` and the `schema.yml`
tests working untouched.

## Running it

```bash
cd dbt_projects/postgres_sao
dbt build
```

In Orchestra, point a dbt Core task at `project_dir: dbt_projects/postgres_sao`.
A matching `profiles.yml` for the connection looks like:

```yaml
dbt_postgres:
  target: prod
  outputs:
    prod:
      type: postgres
      host: <host>
      port: 5432
      user: <user>
      password: <password>
      dbname: <database>
      schema: dbt_sao_demo
      threads: 4
```
