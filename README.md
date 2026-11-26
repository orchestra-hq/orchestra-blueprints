# orchestra-blueprints

Public examples that the [Orchestra docs](https://docs.getorchestra.io) link to.
Each folder is self-contained and has its own README.

## Contents

| Directory | Purpose | Docs |
| --- | --- | --- |
| [`metadata_api/`](metadata_api/) | Export Orchestra metadata to a warehouse with dlt, plus an example pipeline. | Export metadata via REST API and dlt; Metadata to Warehouse template; API introduction |
| [`python/data_assets/`](python/data_assets/) | Self-run asset collection for BigQuery, Databricks and Snowflake through the public asset API. | Asset collection template; Assets |
| [`patterns/run_multiple_pipelines/`](patterns/run_multiple_pipelines/) | Start and monitor several pipelines programmatically via the Orchestra API. | Run multiple pipelines |
| [`patterns/warehouse_savings/`](patterns/warehouse_savings/) | Warehouse cost analysis using the Orchestra API. | dbt Core state management guide |
| [`dbt_projects/state_management/`](dbt_projects/state_management/) | dbt project for the state management tutorial. | dbt Core state management tutorial |

Before moving or renaming anything here, check the docs that link to it; those
links break otherwise.
