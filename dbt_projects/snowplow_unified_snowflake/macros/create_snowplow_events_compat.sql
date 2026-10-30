{#
  SNOWPLOW_TRACKING.ATOMIC.EVENTS is a 22-column subset of the standard atomic
  events table. snowplow_unified / snowplow_utils reference many of the missing
  columns unconditionally (dvce_sent_tstamp in the late-event filter,
  dvce_created_tstamp in dedupe ordering, page_url* / refr_* / mkt_* / br_* in
  the views and sessions models), so this view fills in whichever of them the
  source lacks: derived where possible, typed NULLs otherwise.
  Runs as an on-run-start hook so the view exists before any model compiles;
  the snowplow__atomic_schema var points the package at it.
#}
{% macro create_snowplow_events_compat() %}
  {% if execute %}
    {% set schema = var('snowplow__atomic_schema') %}
    {% do run_query('create schema if not exists ' ~ target.database ~ '.' ~ schema) %}
    {% do run_query(snowplow_events_compat_sql(target.database ~ '.' ~ schema ~ '.events')) %}
  {% endif %}
{% endmacro %}

{% macro snowplow_events_compat_sql(view_name) %}
{%- set source_parts = var('snowplow_raw_events').split('.') -%}
{%- set source = api.Relation.create(database=source_parts[0], schema=source_parts[1], identifier=source_parts[2]) -%}
{%- set existing = adapter.get_columns_in_relation(source) | map(attribute='name') | map('lower') | list -%}
{%- set nulls = [
  ('timestamp_ntz', ['dvce_sent_tstamp', 'load_tstamp']),
  ('varchar', ['page_referrer', 'page_urlscheme', 'page_urlquery', 'page_urlfragment',
               'refr_urlscheme', 'refr_urlpath', 'refr_urlquery', 'refr_urlfragment',
               'refr_medium', 'refr_source', 'refr_term',
               'mkt_medium', 'mkt_source', 'mkt_term', 'mkt_content', 'mkt_campaign', 'mkt_clickid', 'mkt_network',
               'useragent', 'br_lang', 'br_renderengine', 'br_colordepth', 'os_timezone',
               'geo_zipcode', 'geo_region_name', 'geo_timezone']),
  ('float', ['geo_latitude', 'geo_longitude']),
  ('integer', ['pp_xoffset_min', 'pp_xoffset_max', 'pp_yoffset_min', 'pp_yoffset_max',
               'br_viewwidth', 'br_viewheight', 'dvce_screenwidth', 'dvce_screenheight', 'doc_width', 'doc_height']),
] -%}
{#- dvce_created_tstamp: with no device clock in the source, derived_tstamp is
    the closest stand-in, and unified needs it non-null (views test, page-ping
    engaged time).
    web_page context: none is loaded, so each page_view gets its event_id as its
    page view id. Inferred, not tracked: page pings can't be tied to a view. #}
{%- set derived = [
  ('event', 'e.event_name'),
  ('dvce_created_tstamp', 'e.derived_tstamp'),
  ('page_urlhost', 'parse_url(e.page_url, 1):host::varchar'),
  ('page_urlpath', "'/' || parse_url(e.page_url, 1):path::varchar"),
  ('contexts_com_snowplowanalytics_snowplow_web_page_1',
   "case when e.event_name = 'page_view' then array_construct(object_construct('id', e.event_id)) end"),
] -%}
create or replace view {{ view_name }} as
select
  e.*
  {%- for col, expr in derived if col not in existing %},
  {{ expr }} as {{ col }}
  {%- endfor %}
  {%- for type, cols in nulls %}{% for col in cols if col not in existing %},
  null::{{ type }} as {{ col }}
  {%- endfor %}{% endfor %}
from {{ var('snowplow_raw_events') }} e
{#- TEST ONLY: simulated runs see only events loaded before sim_now. #}
{%- if var('sim_now', none) %}
where e.load_tstamp < '{{ var('sim_now') }}'::timestamp_ntz
{%- endif %}
{% endmacro %}
