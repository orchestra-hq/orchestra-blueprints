# fabric_sao

A deliberately small dbt Core project for Fabric, mirroring
[`dbt_projects/bigquery`](../bigquery): a source, a typed staging view, and one
mart table. It exists so the demo account has a Fabric dbt target that is
cheap to build and safe to drop.

- **Profile:** `dbt_fabric` — the profile name that must be defined in the
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

`dbt_sao_demo.raw_orders` is a standing table this project
reads but does not own. It carries an explicit `loaded_at_field`, because
without one everything downstream of the source rebuilds on every run.

The pipeline's `seed raw_orders` step creates it and resets its rows, so there
is nothing to run by hand. The equivalent DDL, for a local build or a manual
reset:

```sql
-- Fabric Warehouse has no CREATE SCHEMA IF NOT EXISTS; run this once and
-- ignore the error if the schema already exists.
CREATE SCHEMA dbt_sao_demo;

DROP TABLE IF EXISTS dbt_sao_demo.raw_orders;
CREATE TABLE dbt_sao_demo.raw_orders (
    order_id    int,
    customer_id int,
    order_date  date,
    status      varchar(32),
    amount      decimal(10, 2)
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

## Fabric specifics

T-SQL, so no `FILTER` clause and `datetime2` rather than `timestamp` in the
source's `loaded_at_field`. `dbt-fabric` talks ODBC: it needs
`Microsoft ODBC Driver 18 for SQL Server` present in whatever runtime executes
the task, which is the one prerequisite here that a `requirements.txt` cannot
satisfy on its own.

## Running it

```bash
cd dbt_projects/fabric_sao
dbt build
```

In Orchestra, point a dbt Core task at `project_dir: dbt_projects/fabric_sao`.
A matching `profiles.yml` for the connection looks like:

```yaml
dbt_fabric:
  target: prod
  outputs:
    prod:
      type: fabric
      driver: 'ODBC Driver 18 for SQL Server'
      server: <workspace>.datawarehouse.fabric.microsoft.com
      database: <warehouse>
      schema: dbt_sao_demo
      authentication: ServicePrincipal
      tenant_id: <tenant-id>
      client_id: <client-id>
      client_secret: <client-secret>
      threads: 4
```
