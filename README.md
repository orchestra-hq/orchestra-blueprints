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

Contains a dbt project.

### dlt

Contains a dlt project, for running dlt pipelines