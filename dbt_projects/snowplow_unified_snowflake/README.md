# snowplow_unified_snowflake

Runs the [Snowplow Unified data model](https://docs.snowplow.io/docs/modeling-your-data/modeling-your-data-with-dbt/dbt-models/dbt-unified-data-model/)
(`snowplow/snowplow_unified` 1.0.1) on **dbt v2** (`dbt-oss`, installed by
Orchestra with `package_manager: UV`) against Snowflake.

Source: `SNOWPLOW_TRACKING.ATOMIC.EVENTS`, via `snowplow__database` /
`snowplow__atomic_schema`. Same table as [`snowplow_snowflake_sao`](../snowplow_snowflake_sao).

Orchestra pipeline: "Snowplow Unified on dbt v2" in the Orchestra Demo Account,
inputs `dbt_branch` / `dbt_command`.

## Error log

| # | Error | Fix |
| --- | --- | --- |
