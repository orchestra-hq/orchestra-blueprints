# dbt_projects structure

This directory contains standalone dbt blueprint examples.

## Naming conventions

- Subprojects should use snake_case directory names.
- Each subproject should include an uppercase `README.md` file.
- Keep project-specific dependencies and config files inside each subproject.

## Current subprojects

- `azure_fabric` - UNUSED
- `bigquery` - Small source -> staging -> mart project for the BigQuery demo connection
- `clickhouse` - Sample ClickHouse integration
- `databricks`
- `duckdb_example` - UNUSED
- `fabric_sao` - `bigquery` mirrored onto Fabric, for the multi-warehouse SAO demo
- `motherduck_postgres` - UNUSED
- `motherduck_s3`
- `motherduck_sao` - `bigquery` mirrored onto MotherDuck, for the multi-warehouse SAO demo
- `postgres` - UNUSED
- `postgres_sao` - `bigquery` mirrored onto Postgres, for the multi-warehouse SAO demo
- `redshift_sao` - `bigquery` mirrored onto Redshift, for the multi-warehouse SAO demo
- `snowflake`
- `state_management` - UNUSED

The four `*_sao` projects and `bigquery` are all the same three-node DAG
(`raw_orders` source -> `stg_orders` view -> `orders_daily` table) in each
warehouse's dialect, so
[`orchestra/dbt/sao_multi_warehouse.yml`](../orchestra/dbt/sao_multi_warehouse.yml)
can run the identical state-aware-orchestration A/B test against any of them.
