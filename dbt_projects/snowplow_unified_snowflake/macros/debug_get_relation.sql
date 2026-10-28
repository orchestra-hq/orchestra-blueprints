{# Temporary: checks how dbt v2's adapter.get_relation resolves case. Remove once diagnosed. #}
{% macro debug_get_relation() %}
  {% for schema, ident in [
      ('PUBLIC_scratch', 'snowplow_unified_base_sessions_this_run'),
      ('PUBLIC_SCRATCH', 'snowplow_unified_base_sessions_this_run'),
      ('PUBLIC_SCRATCH', 'SNOWPLOW_UNIFIED_BASE_SESSIONS_THIS_RUN'),
      ('public_scratch', 'snowplow_unified_base_sessions_this_run'),
      ('PUBLIC_scratch', 'snowplow_unified_base_new_event_limits'),
  ] %}
    {% set r = adapter.get_relation(database=target.database, schema=schema, identifier=ident) %}
    {% do log('DEBUG_GET_RELATION ' ~ schema ~ '.' ~ ident ~ ' -> ' ~ r, info=true) %}
  {% endfor %}
  {% set m = ref('snowplow_unified_base_sessions_this_run') %}
  {% do log('DEBUG_GET_RELATION ref -> db=' ~ m.database ~ ' schema=' ~ m.schema ~ ' name=' ~ m.name ~ ' found=' ~ adapter.get_relation(database=m.database, schema=m.schema, identifier=m.name), info=true) %}
{% endmacro %}
