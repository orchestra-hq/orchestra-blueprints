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
| 1 | `dbt deps`: `PackageVersionMismatch` for snowplow_unified and snowplow_utils (`require-dbt-version <2.0.0`) | None needed. dbt-oss 2.0.8 only warns, so no vendoring. |
| 2 | `snowplow_unified_base_sessions_lifecycle_manifest`: `invalid identifier 'DVCE_SENT_TSTAMP'`. snowplow_utils' late-event filter is unconditional; `days_late_allowed: -1` doesn't remove it (unlike normalize). | `ATOMIC.EVENTS` turned out to have only 22 columns (checked via `INFORMATION_SCHEMA`), with no dvce_*, page_url* parts, refr_*, mkt_*, br_*, useragent, or web_page context. An `on-run-start` hook ([macros/create_snowplow_events_compat.sql](macros/create_snowplow_events_compat.sql)) builds `<target db>.SNOWPLOW_ATOMIC_COMPAT.EVENTS` over the raw table, adding the missing columns as typed NULLs. It also derives `page_urlhost`/`page_urlpath` from `page_url` and synthesizes a web_page context (`id = event_id`) on page_view events. `snowplow__atomic_schema` points the package at the view, and `snowplow__allow_null_dvce_tstamps: true` makes the late filter coalesce to `collector_tstamp`. `days_late_allowed` is back to its default of 3: with the coalesce, `-1` would filter out every row. |
