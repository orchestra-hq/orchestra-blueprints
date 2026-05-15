# orchestra-blueprints

Reference blueprints for building and operating Orchestra-driven data platforms
in a monorepo. The repository includes pipeline definitions, worker scripts, and
integration examples across multiple tooling stacks.

## Codebase structure

| Directory | Purpose |
| --- | --- |
| [`azure/`](azure/) | Azure ML example assets and pipeline support files. |
| [`bauplan/`](bauplan/) | Bauplan project examples and helper scripts. |
| [`dbt_projects/`](dbt_projects/) | dbt blueprint projects for multiple warehouses. |
| [`dlt/`](dlt/) | dlt ingestion examples and runner scripts. |
| [`estuary/`](estuary/) | Estuary-related sample configuration files. |
| [`metadata_api/`](metadata_api/) | Metadata API ingestion pipeline and worker code. |
| [`multi_workspace_test/`](multi_workspace_test/) | Multi-workspace test pipeline examples. |
| [`orchestra/`](orchestra/) | Orchestra pipeline YAML definitions. |
| [`patterns/`](patterns/) | Reusable implementation patterns and demos. |
| [`python/`](python/) | General-purpose Python workers and integrations. |

## Directory notes

### Orchestra

`orchestra/` contains runnable pipeline definitions used by the examples in this
repository.

### dbt Projects

`dbt_projects/` includes warehouse-specific dbt setups (for example, Snowflake,
Postgres, Databricks, and Azure Fabric) that can be paired with Orchestra
pipelines.

### Metadata API

`metadata_api/` shows how to ingest Orchestra metadata with dlt and run checks
in downstream warehouses. It includes an example Orchestra pipeline file and
runtime script.

### Patterns

`patterns/` holds reusable workflow patterns, including the run-multiple
pipelines utility.

### Python workers

`python/` contains worker scripts that Orchestra can execute via Python task
integrations.
