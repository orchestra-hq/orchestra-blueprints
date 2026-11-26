# dbt_projects structure

This directory contains standalone dbt blueprint examples.

## Naming conventions

- Subprojects should use snake_case directory names.
- Each subproject should include an uppercase `README.md` file.
- Keep project-specific dependencies and config files inside each subproject.

## Current subprojects

- `azure_fabric` - UNUSED
- `duckdb_example` - UNUSED
- `fabric_sao` - Small source -> staging -> mart project on Fabric, for the multi-warehouse SAO demo
- `motherduck_postgres` - UNUSED
- `motherduck_s3`
- `motherduck_sao` - Small source -> staging -> mart project on MotherDuck, for the multi-warehouse SAO demo
- `postgres` - UNUSED
- `postgres_sao` - Small source -> staging -> mart project on Postgres, for the multi-warehouse SAO demo
- `redshift_sao` - Small source -> staging -> mart project on Redshift, for the multi-warehouse SAO demo
- `state_management` - UNUSED

The `*_sao` projects are all the same three-node DAG
(`raw_orders` source -> `stg_orders` view -> `orders_daily` table) in each
warehouse's dialect, so the same state-aware-orchestration A/B test can run
against any of them.
