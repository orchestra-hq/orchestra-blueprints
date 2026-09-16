{{ config(
    tags = "snowplow_normalize_incremental",
    materialized = "incremental",
    unique_key = "unique_id",
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

select
    event_id
    , {{var("snowplow__partition_tstamp")}}
    {% if target.type in ['databricks', 'spark'] -%}
    , DATE({{var("snowplow__partition_tstamp")}}) as {{var("snowplow__partition_tstamp")}}_date
    {%- endif %}
    , event_name
    , 'page_events_1' as event_table_name
    , event_id||'-'||'page_events_1' as unique_id
from
    {{ ref('snowplow_normalize_base_events_this_run') }}
where
    event_name in ('page_view','page_ping')
    and {{ snowplow_utils.is_run_with_new_events("snowplow_normalize") }}
        
UNION ALL

select
    event_id
    , {{var("snowplow__partition_tstamp")}}
    {% if target.type in ['databricks', 'spark'] -%}
    , DATE({{var("snowplow__partition_tstamp")}}) as {{var("snowplow__partition_tstamp")}}_date
    {%- endif %}
    , event_name
    , 'snowplow_link_click_1' as event_table_name
    , event_id||'-'||'snowplow_link_click_1' as unique_id
from
    {{ ref('snowplow_normalize_base_events_this_run') }}
where
    event_name in ('link_click')
    and {{ snowplow_utils.is_run_with_new_events("snowplow_normalize") }}
        
UNION ALL

select
    event_id
    , {{var("snowplow__partition_tstamp")}}
    {% if target.type in ['databricks', 'spark'] -%}
    , DATE({{var("snowplow__partition_tstamp")}}) as {{var("snowplow__partition_tstamp")}}_date
    {%- endif %}
    , event_name
    , 'snowplow_application_error_1' as event_table_name
    , event_id||'-'||'snowplow_application_error_1' as unique_id
from
    {{ ref('snowplow_normalize_base_events_this_run') }}
where
    event_name in ('application_error')
    and {{ snowplow_utils.is_run_with_new_events("snowplow_normalize") }}
        
UNION ALL

select
    event_id
    , {{var("snowplow__partition_tstamp")}}
    {% if target.type in ['databricks', 'spark'] -%}
    , DATE({{var("snowplow__partition_tstamp")}}) as {{var("snowplow__partition_tstamp")}}_date
    {%- endif %}
    , event_name
    , 'snowplow_consent_preferences_1' as event_table_name
    , event_id||'-'||'snowplow_consent_preferences_1' as unique_id
from
    {{ ref('snowplow_normalize_base_events_this_run') }}
where
    event_name in ('consent_preferences')
    and {{ snowplow_utils.is_run_with_new_events("snowplow_normalize") }}
        
UNION ALL

select
    event_id
    , {{var("snowplow__partition_tstamp")}}
    {% if target.type in ['databricks', 'spark'] -%}
    , DATE({{var("snowplow__partition_tstamp")}}) as {{var("snowplow__partition_tstamp")}}_date
    {%- endif %}
    , event_name
    , 'snowplow_cmp_visible_1' as event_table_name
    , event_id||'-'||'snowplow_cmp_visible_1' as unique_id
from
    {{ ref('snowplow_normalize_base_events_this_run') }}
where
    event_name in ('cmp_visible')
    and {{ snowplow_utils.is_run_with_new_events("snowplow_normalize") }}
        
UNION ALL

select
    event_id
    , {{var("snowplow__partition_tstamp")}}
    {% if target.type in ['databricks', 'spark'] -%}
    , DATE({{var("snowplow__partition_tstamp")}}) as {{var("snowplow__partition_tstamp")}}_date
    {%- endif %}
    , event_name
    , 'snowplow_quote_requested_1' as event_table_name
    , event_id||'-'||'snowplow_quote_requested_1' as unique_id
from
    {{ ref('snowplow_normalize_base_events_this_run') }}
where
    event_name in ('quote_requested')
    and {{ snowplow_utils.is_run_with_new_events("snowplow_normalize") }}
        
UNION ALL

select
    event_id
    , {{var("snowplow__partition_tstamp")}}
    {% if target.type in ['databricks', 'spark'] -%}
    , DATE({{var("snowplow__partition_tstamp")}}) as {{var("snowplow__partition_tstamp")}}_date
    {%- endif %}
    , event_name
    , 'snowplow_article_interaction_1' as event_table_name
    , event_id||'-'||'snowplow_article_interaction_1' as unique_id
from
    {{ ref('snowplow_normalize_base_events_this_run') }}
where
    event_name in ('article_interaction')
    and {{ snowplow_utils.is_run_with_new_events("snowplow_normalize") }}
        
UNION ALL

select
    event_id
    , {{var("snowplow__partition_tstamp")}}
    {% if target.type in ['databricks', 'spark'] -%}
    , DATE({{var("snowplow__partition_tstamp")}}) as {{var("snowplow__partition_tstamp")}}_date
    {%- endif %}
    , event_name
    , 'snowplow_user_identified_1' as event_table_name
    , event_id||'-'||'snowplow_user_identified_1' as unique_id
from
    {{ ref('snowplow_normalize_base_events_this_run') }}
where
    event_name in ('user_identified')
    and {{ snowplow_utils.is_run_with_new_events("snowplow_normalize") }}
        
UNION ALL

select
    event_id
    , {{var("snowplow__partition_tstamp")}}
    {% if target.type in ['databricks', 'spark'] -%}
    , DATE({{var("snowplow__partition_tstamp")}}) as {{var("snowplow__partition_tstamp")}}_date
    {%- endif %}
    , event_name
    , 'snowplow_identity_merge_1' as event_table_name
    , event_id||'-'||'snowplow_identity_merge_1' as unique_id
from
    {{ ref('snowplow_normalize_base_events_this_run') }}
where
    event_name in ('identity_merge')
    and {{ snowplow_utils.is_run_with_new_events("snowplow_normalize") }}
        
UNION ALL

select
    event_id
    , {{var("snowplow__partition_tstamp")}}
    {% if target.type in ['databricks', 'spark'] -%}
    , DATE({{var("snowplow__partition_tstamp")}}) as {{var("snowplow__partition_tstamp")}}_date
    {%- endif %}
    , event_name
    , 'snowplow_percent_progress_event_1' as event_table_name
    , event_id||'-'||'snowplow_percent_progress_event_1' as unique_id
from
    {{ ref('snowplow_normalize_base_events_this_run') }}
where
    event_name in ('percent_progress_event')
    and {{ snowplow_utils.is_run_with_new_events("snowplow_normalize") }}
        
UNION ALL

select
    event_id
    , {{var("snowplow__partition_tstamp")}}
    {% if target.type in ['databricks', 'spark'] -%}
    , DATE({{var("snowplow__partition_tstamp")}}) as {{var("snowplow__partition_tstamp")}}_date
    {%- endif %}
    , event_name
    , 'snowplow_play_event_1' as event_table_name
    , event_id||'-'||'snowplow_play_event_1' as unique_id
from
    {{ ref('snowplow_normalize_base_events_this_run') }}
where
    event_name in ('play_event')
    and {{ snowplow_utils.is_run_with_new_events("snowplow_normalize") }}
        
UNION ALL

select
    event_id
    , {{var("snowplow__partition_tstamp")}}
    {% if target.type in ['databricks', 'spark'] -%}
    , DATE({{var("snowplow__partition_tstamp")}}) as {{var("snowplow__partition_tstamp")}}_date
    {%- endif %}
    , event_name
    , 'snowplow_intervention_receive_1' as event_table_name
    , event_id||'-'||'snowplow_intervention_receive_1' as unique_id
from
    {{ ref('snowplow_normalize_base_events_this_run') }}
where
    event_name in ('intervention_receive')
    and {{ snowplow_utils.is_run_with_new_events("snowplow_normalize") }}
        
UNION ALL

select
    event_id
    , {{var("snowplow__partition_tstamp")}}
    {% if target.type in ['databricks', 'spark'] -%}
    , DATE({{var("snowplow__partition_tstamp")}}) as {{var("snowplow__partition_tstamp")}}_date
    {%- endif %}
    , event_name
    , 'snowplow_intervention_handle_1' as event_table_name
    , event_id||'-'||'snowplow_intervention_handle_1' as unique_id
from
    {{ ref('snowplow_normalize_base_events_this_run') }}
where
    event_name in ('intervention_handle')
    and {{ snowplow_utils.is_run_with_new_events("snowplow_normalize") }}
        
UNION ALL

select
    event_id
    , {{var("snowplow__partition_tstamp")}}
    {% if target.type in ['databricks', 'spark'] -%}
    , DATE({{var("snowplow__partition_tstamp")}}) as {{var("snowplow__partition_tstamp")}}_date
    {%- endif %}
    , event_name
    , 'snowplow_cta_clicked_1' as event_table_name
    , event_id||'-'||'snowplow_cta_clicked_1' as unique_id
from
    {{ ref('snowplow_normalize_base_events_this_run') }}
where
    event_name in ('cta_clicked')
    and {{ snowplow_utils.is_run_with_new_events("snowplow_normalize") }}
        
UNION ALL

select
    event_id
    , {{var("snowplow__partition_tstamp")}}
    {% if target.type in ['databricks', 'spark'] -%}
    , DATE({{var("snowplow__partition_tstamp")}}) as {{var("snowplow__partition_tstamp")}}_date
    {%- endif %}
    , event_name
    , 'snowplow_assessment_completed_1' as event_table_name
    , event_id||'-'||'snowplow_assessment_completed_1' as unique_id
from
    {{ ref('snowplow_normalize_base_events_this_run') }}
where
    event_name in ('assessment_completed')
    and {{ snowplow_utils.is_run_with_new_events("snowplow_normalize") }}
        
UNION ALL

select
    event_id
    , {{var("snowplow__partition_tstamp")}}
    {% if target.type in ['databricks', 'spark'] -%}
    , DATE({{var("snowplow__partition_tstamp")}}) as {{var("snowplow__partition_tstamp")}}_date
    {%- endif %}
    , event_name
    , 'snowplow_frontpage_slot_interaction_1' as event_table_name
    , event_id||'-'||'snowplow_frontpage_slot_interaction_1' as unique_id
from
    {{ ref('snowplow_normalize_base_events_this_run') }}
where
    event_name in ('frontpage_slot_interaction')
    and {{ snowplow_utils.is_run_with_new_events("snowplow_normalize") }}
        
UNION ALL

select
    event_id
    , {{var("snowplow__partition_tstamp")}}
    {% if target.type in ['databricks', 'spark'] -%}
    , DATE({{var("snowplow__partition_tstamp")}}) as {{var("snowplow__partition_tstamp")}}_date
    {%- endif %}
    , event_name
    , 'snowplow_frontpage_composed_1' as event_table_name
    , event_id||'-'||'snowplow_frontpage_composed_1' as unique_id
from
    {{ ref('snowplow_normalize_base_events_this_run') }}
where
    event_name in ('frontpage_composed')
    and {{ snowplow_utils.is_run_with_new_events("snowplow_normalize") }}
        
UNION ALL

select
    event_id
    , {{var("snowplow__partition_tstamp")}}
    {% if target.type in ['databricks', 'spark'] -%}
    , DATE({{var("snowplow__partition_tstamp")}}) as {{var("snowplow__partition_tstamp")}}_date
    {%- endif %}
    , event_name
    , 'snowplow_package_configured_1' as event_table_name
    , event_id||'-'||'snowplow_package_configured_1' as unique_id
from
    {{ ref('snowplow_normalize_base_events_this_run') }}
where
    event_name in ('package_configured')
    and {{ snowplow_utils.is_run_with_new_events("snowplow_normalize") }}
        
UNION ALL

select
    event_id
    , {{var("snowplow__partition_tstamp")}}
    {% if target.type in ['databricks', 'spark'] -%}
    , DATE({{var("snowplow__partition_tstamp")}}) as {{var("snowplow__partition_tstamp")}}_date
    {%- endif %}
    , event_name
    , 'snowplow_ad_interaction_1' as event_table_name
    , event_id||'-'||'snowplow_ad_interaction_1' as unique_id
from
    {{ ref('snowplow_normalize_base_events_this_run') }}
where
    event_name in ('ad_interaction')
    and {{ snowplow_utils.is_run_with_new_events("snowplow_normalize") }}
        