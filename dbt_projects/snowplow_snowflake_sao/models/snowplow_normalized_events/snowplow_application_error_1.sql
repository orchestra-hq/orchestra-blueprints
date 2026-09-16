{{ config(
    tags = "snowplow_normalize_incremental",
    materialized = "incremental",
    unique_key = "event_id",
    partition_by = snowplow_utils.get_value_by_target_type(bigquery_val={
      "field":  var("snowplow__partition_tstamp"),
      "data_type": "timestamp"
    }, databricks_val=snowplow_normalize.rename_partition_tstamp_date()),
    sql_header=snowplow_utils.set_query_tag(var('snowplow__query_tag', 'snowplow_dbt')),
    tblproperties={
      'delta.autoOptimize.optimizeWrite' : 'true',
      'delta.autoOptimize.autoCompact' : 'true'
    },
    meta={'upsert_date_key': var("snowplow__partition_tstamp"), 'snowplow_optimize': true}
) }}

{%- set event_names = ['application_error'] -%}
{%- set flat_cols = ['app_id', 'domain_userid', 'page_url', 'platform'] -%}
{%- set sde_cols = ['UNSTRUCT_EVENT_COM_SNOWPLOWANALYTICS_SNOWPLOW_APPLICATION_ERROR_1_0_2'] -%}
{%- set sde_keys = [['programmingLanguage', 'message', 'threadName', 'threadId', 'stackTrace', 'causeStackTrace', 'lineNumber', 'className', 'exceptionName', 'isFatal', 'lineColumn', 'fileName']] -%}
{%- set sde_types = [['string', 'string', 'string', 'integer', 'string', 'string', 'integer', 'string', 'string', 'boolean', 'integer', 'string']] -%}
{%- set sde_aliases = ['error'] -%}
{%- set context_cols = [] -%}
{%- set context_keys = [] -%}
{%- set context_types = [] -%}
{%- set context_alias = [] -%}

{{ snowplow_normalize.normalize_events(
    event_names,
    flat_cols,
    sde_cols,
    sde_keys,
    sde_types,
    sde_aliases,
    context_cols,
    context_keys,
    context_types,
    context_alias
) }}
