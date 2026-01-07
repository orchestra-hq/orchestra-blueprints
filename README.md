# orchestra-blueprints

This repo includes all the code you need to develop a fully-featured data platform capable of running end-to-end data pipelines across different tools, using a monorepo structure.

## Codebase Structure

1. [Analytics](#analytics)
1. [Bauplan](#bauplan)
1. [dbt Projects](#dbt)
1. [dlt](#dlt)
1. [Metadata API](#metadata_api)
1. [Orchestra](#orchestra)
1. [Python](#python)
1. [Run multiple pipelines](#run-multiple-pipelines)
1. [Sensors](#sensors)

### Orchestra

The Orchestra directory contains the required code to run Orchestra as the overarching Orchestration engine. The .yml definitions are sufficient to provide the required logic to orchestrate pipelines, run data quality tests, populate the data catalog, and provide visibility across the entire data stack.

Components that require in-platform configuration are:

- Alerts
- Data Products
- Role-Based Access Control and User Provisioning
- Integrations (credentials)
- Environments

### Analytics

Contains Python scripts to perform analytics on your Orchestra Metadata. Each script in this folder will contain a README with further instructions on usage.

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

### Run multiple pipelines

If you want to run multiple pipelines in a single script, you can use the `run_multiple_pipelines.py` script. This can be useful for programmatically invoking the same pipeline manually for full refreshes or backfilling data across multiple sources.

### Bauplan

Contains template code for executing Bauplan jobs. For more information refer to [this article](https://www.getorchestra.io/blog/this-pattern-is-a-rude-awakening-for-the-modern-data-stack), which shows how you can build a Simple Data Stack with just Orchestra and Bauplan.

### Sensors

Contains some Python code to run custom Sensors in Orchestra. Note - Orchestra supports native sensors for many integrations now.

### Metadata_API

Contains example dlt code for ingesting Orchestra Metadata via the REST API, and loading into a warehouse. This API contains information about your pipelines, including runs, task runs, and operations. You can use this to store orchestration data in another system such as Snowflake or BigQuery for internal reporting and monitoring. Also provided is an example Orchestra pipeline YAML to run similar pipelines in your account.

Credentials can be added to `.dlt/secrets.toml` in the dlt directory - this file is Git ignored. Alternatively, if running in Orchestra, you can add the credentials in the connection object JSON:

```json
{
    "DESTINATION__SNOWFLAKE__CREDENTIALS__DATABASE": "SNOWFLAKE_DATABASE",
    "DESTINATION__SNOWFLAKE__CREDENTIALS__PASSWORD": "********",
    ...
}
```

Note: this API is available to enterprise customers only.
