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
| [`python/dummy_pipeline/`](python/dummy_pipeline/) | Dummy end-to-end blueprint: a Python extract feeding a dbt build, with alerts and anomaly detection at pipeline, task and dbt-node level. |
| [`python/lineage/`](python/lineage/) | dlt metadata extracts (Lightdash, BigQuery, Fivetran) that publish an end-to-end lineage graph into Orchestra. |
| [`patterns/run_multiple_pipelines/`](patterns/run_multiple_pipelines/) | Examples for programmatic multi-pipeline runs (Orchestra API patterns). |
| [`patterns/warehouse_savings/`](patterns/warehouse_savings/) | Warehouse optimization and analytics (Orchestra API pattern). |
| [`patterns/duckdb_quality/`](patterns/duckdb_quality/) | Declarative Snowflake data quality tests driven by the DuckDB CLI. |

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
dlt, and `publish_lineage.py` queries the landed tables directly (see
`queries.py`) and publishes the result through Orchestra's `POST /assets` and
`POST /assets/dependencies` endpoints so the whole stack shows up under Data
assets → Lineage. Adding another platform is three localised edits; see
[`python/lineage/README.md`](python/lineage/README.md) for the full setup.

### Dummy end-to-end blueprint

`orchestra/dummy_end_to_end.yml` is the smallest complete example of an
Orchestra pipeline with monitoring wired all the way through: a Python extract
([`python/dummy_pipeline/`](python/dummy_pipeline/)) whose Task output feeds a
dbt Core build ([`dbt_projects/dummy_motherduck/`](dbt_projects/dummy_motherduck/)),
carrying status `alerts` plus duration `anomalies` at pipeline, Task and dbt-node
level. Start here when building a new pipeline from scratch.

### Python workers

`python/` contains Python modules used by the repo’s demos.

Most subfolders are intended to be executed by Orchestra via Python task
integrations.
