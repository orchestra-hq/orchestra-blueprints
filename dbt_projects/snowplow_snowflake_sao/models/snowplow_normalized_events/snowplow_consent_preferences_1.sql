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

{%- set event_names = ['consent_preferences'] -%}
{%- set flat_cols = ['app_id', 'domain_userid', 'page_url'] -%}
{%- set sde_cols = ['UNSTRUCT_EVENT_COM_SNOWPLOWANALYTICS_SNOWPLOW_CONSENT_PREFERENCES_1_0_0'] -%}
{%- set sde_keys = [['eventType', 'basisForProcessing', 'consentUrl', 'consentVersion', 'consentScopes', 'domainsApplied', 'gdprApplies']] -%}
{%- set sde_types = [['string', 'string', 'string', 'string', 'array', 'array', 'boolean']] -%}
{%- set sde_aliases = ['consent'] -%}
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
