{#
  SNOWPLOW_TRACKING.ATOMIC.EVENTS is a 22-column subset of the standard atomic
  events table. snowplow_unified / snowplow_utils reference many of the missing
  columns unconditionally (dvce_sent_tstamp in the late-event filter,
  dvce_created_tstamp in dedupe ordering, page_url* / refr_* / mkt_* / br_* in
  the views and sessions models), so this view fills them in as typed NULLs.
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
create or replace view {{ view_name }} as
select
  e.*,
  -- ponytail: hardcoded column list; if the source table gains one of these
  -- columns the view fails with a duplicate column, drop it from the list then.
  e.event_name as event,
  -- No device clock in the source. derived_tstamp is the closest stand-in, and
  -- unified needs this column non-null (views test, page-ping engaged time).
  e.derived_tstamp as dvce_created_tstamp,
  parse_url(e.page_url, 1):host::varchar as page_urlhost,
  '/' || parse_url(e.page_url, 1):path::varchar as page_urlpath,
  -- No web_page context is loaded, so each page_view gets its event_id as its
  -- page view id. Inferred, not tracked: page pings can't be tied to a view.
  case when e.event_name = 'page_view' then array_construct(object_construct('id', e.event_id)) end
    as contexts_com_snowplowanalytics_snowplow_web_page_1
  {%- for type, cols in nulls %}{% for col in cols %},
  null::{{ type }} as {{ col }}
  {%- endfor %}{% endfor %}
from {{ var('snowplow_raw_events') }} e
{% endmacro %}
