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
| [`python/lineage/`](python/lineage/) | dlt metadata extracts (Lightdash, BigQuery, Fivetran) that publish an end-to-end lineage graph into Orchestra. |
| [`patterns/run_multiple_pipelines/`](patterns/run_multiple_pipelines/) | Examples for programmatic multi-pipeline runs (Orchestra API patterns). |
| [`patterns/warehouse_savings/`](patterns/warehouse_savings/) | Warehouse optimization and analytics (Orchestra API pattern). |

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
`patterns/` holds reusable workflow patterns and supporting examples.

### Run multiple pipelines

`patterns/run_multiple_pipelines/` contains patterns for interacting with
Orchestra as a platform (programmatic multi-pipeline runs via the API).

### Warehouse savings

`patterns/warehouse_savings/` contains the warehouse optimization and analytics
pattern examples, implemented as an Orchestra API client/analysis.

### Platform lineage

`python/lineage/` extracts metadata from Lightdash, BigQuery, and Fivetran with
dlt, models it into `lineage_assets` / `lineage_edges` with
`dbt_projects/bigquery_lineage/`, and publishes the result through Orchestra's
`POST /assets` and `POST /assets/dependencies` endpoints so the whole stack shows
up under Data assets → Lineage. Adding another platform is four localised edits.
Requires a dbt Core connection bound to this repository and mapped to the
`DBT_CORE_BIGQUERY` environment variable; see
[`python/lineage/README.md`](python/lineage/README.md) for the full setup.

### Python workers

`python/` contains Python modules used by the repo’s demos.

Most subfolders are intended to be executed by Orchestra via Python task
integrations.
