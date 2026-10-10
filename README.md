# orchestra-blueprints

Reference blueprints for building and operating Orchestra-driven data platforms
in a monorepo. The repository includes pipeline definitions, worker scripts, and
integration examples across multiple tooling stacks.

## Codebase structure

| Directory | Purpose |
| --- | --- |
| [`python/azure/`](python/azure/) | Azure ML example assets and pipeline support files. |
| [`python/bauplan/`](python/bauplan/) | Bauplan project examples and helper scripts. |
| [`dbt_projects/`](dbt_projects/) | dbt blueprint projects for multiple warehouses. |
| [`dlt/`](dlt/) | dlt ingestion examples and runner scripts. |
| [`estuary/`](estuary/) | Estuary-related sample configuration files. |
| [`metadata_api/`](metadata_api/) | Metadata API ingestion pipeline and worker code. |
| [`multi_workspace_test/`](multi_workspace_test/) | Multi-workspace test pipeline examples. |
| [`orchestra/`](orchestra/) | Orchestra pipeline YAML definitions. |
| [`patterns/`](patterns/) | Reusable implementation patterns and demos. |
| [`python/`](python/) | General-purpose Python workers and integrations. |
| [`python/bigquery_assets/`](python/bigquery_assets/) | Self-run BigQuery asset collection that writes tables, views and lineage through the public asset API. |
| [`python/lineage/`](python/lineage/) | dlt metadata extracts (Lightdash, BigQuery, Fivetran) that publish an end-to-end lineage graph into Orchestra. |
| [`patterns/run_multiple_pipelines/`](patterns/run_multiple_pipelines/) | Examples for programmatic multi-pipeline runs (Orchestra API patterns). |
| [`patterns/warehouse_savings/`](patterns/warehouse_savings/) | Warehouse optimization and analytics (Orchestra API pattern). |
| [`patterns/duckdb_quality/`](patterns/duckdb_quality/) | Declarative Snowflake data quality tests driven by the DuckDB CLI. |

## Directory notes

### HOW WE BUILD PIPELINES

1. If you're reading this, make an ELT pipeline basically classifying jobs into types; extract, Load, transform or downstream. Example EL jobs are Fivetran, Kubernetes jobs, python jobs. Example T jobs are Snowflake Tasks or Coalesce or dbt core. Example Downstream are dashboard refreshes
2. If you are asked to add a python script, add an arbitrary python script or use an existing one in this repo, simulating a load of data
3. Depending on the credentials available choose a working Coalesce or dbt project to run as the T step
4. Depending on the credentials available, pick something adequate for your downstream tasks as well

Always fetch into the underlying platforms to get actual Job IDs etc.
Always add alerts, adding Slack, Teams if available and adding email hugo@getorchestra.io.
Add a task-level alert to any dbt Tasks; not just the pipeline
Automatically add anomaly detection to Pipelines


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
`patterns/` holds reusable workflow patterns and supporting examples.

### Run multiple pipelines

`patterns/run_multiple_pipelines/` contains patterns for interacting with
Orchestra as a platform (programmatic multi-pipeline runs via the API).

### Warehouse savings

`patterns/warehouse_savings/` contains the warehouse optimization and analytics
pattern examples, implemented as an Orchestra API client/analysis.

### Platform lineage

`python/lineage/` extracts metadata from Lightdash, BigQuery, and Fivetran with
dlt, and `publish_lineage.py` queries the landed tables directly (see
`queries.py`) and publishes the result through Orchestra's `POST /assets` and
`POST /assets/dependencies` endpoints so the whole stack shows up under Data
assets → Lineage. Adding another platform is three localised edits; see
[`python/lineage/README.md`](python/lineage/README.md) for the full setup.

### Python workers

`python/` contains Python modules used by the repo’s demos.

Most subfolders are intended to be executed by Orchestra via Python task
integrations.



