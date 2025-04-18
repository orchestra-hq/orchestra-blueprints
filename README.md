# orchestra-blueprints

This repo includes all the code you need to develop a fully-featured data platform capable of running end-to-end data pipelines across different tools, using a monorepository structure.

## Codebase Structure

### Orchestra

The Orchestra directory contains the required code to run Orchestra as the overarching Orchestration engine. The .yml definitions are sufficient to provide the required logic to orchestrate pipelines, run data quality tests, populate the data catalog, and provide visibility across the entire data stack.

Components that require in-platform configuration are:

- Alerts
- Data Products
- Role-Based Access Control and User Provisioning
- Integrations (credentials)
- Environments


### dbt

Contains dbt projects:

- Fabric
- BigQuery (to be added)
- Databricks (to be added)
- Postgres
- Snowflake

You should not need the extra folder structure, i.e. dbt/project_name/project_contents. You can just have dbt/project_contents.

You may wish to have multiple directories here for different teams' projects in the same folder _and_ adopting a monorepo strategy.

### dlt

Contains a dlt project, for running dlt pipelines

### Python

Contains python code for data movement.

Note - Orchestra adopts a highly modular architecture which means parameters are set _in_ Orchestra which should be passed down to the python tasks at runtime. Think of your python scripts as all-purpose workers that know how to fetch data different sources like Salesforce, SAP, Postgres. They also know how to apply specific logical patterns to specific objects like Accounts, Orders, Customers, Shipments and so-on. They just need to be told _which_ sources and objects to ingest.

One invocation of a script per table per run is recommended for optimal concurrency.

### Bauplan

Contains template code for executing Bauplan jobs