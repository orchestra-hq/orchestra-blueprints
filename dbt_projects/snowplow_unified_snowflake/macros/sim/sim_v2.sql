{#
  TEST ONLY: harness for the v2 tuning test. Every variant starts from the same
  seeded state (a zero-copy clone), runs the same daily increments, and is
  scored against the raw events rather than against another variant.
#}

{% macro sim_schemas(case) %}
  {% set prefix = (target.schema ~ '_' ~ case ~ '_') | upper %}
  {% set res = run_query("select schema_name from " ~ target.database ~ ".information_schema.schemata") %}
  {% set out = [] %}
  {% for s in res.columns[0].values() if s.upper().startswith(prefix) %}{% do out.append(s.upper()) %}{% endfor %}
  {{ return(out) }}
{% endmacro %}

{# Clones every output schema of from_case into the current sim_case. #}
{% macro sim_clone(from_case) %}
  {% set src = (target.schema ~ '_' ~ from_case ~ '_') | upper %}
  {% set dst = (target.schema ~ '_' ~ var('sim_case') ~ '_') | upper %}
  {% for s in sim_schemas(from_case) %}
    {% do run_query('create or replace schema ' ~ target.database ~ '.' ~ dst ~ s[src | length:] ~ ' clone ' ~ target.database ~ '.' ~ s) %}
    {% do log('cloned ' ~ s ~ ' -> ' ~ dst ~ s[src | length:], info=True) %}
  {% endfor %}
{% endmacro %}

{#
  Gives the seeded state about a year of history: each table gets `copies`
  copies of its rows, shifted back period_days at a time, with session and
  view ids suffixed so they stay unique. user_identifier is kept, so returning
  users own sessions across the whole history, as they would in production.
  Rows are rewritten in start_tstamp order, as daily appends would leave them.
#}
{% macro sim_inflate_history(copies=12, period_days=30) %}
  {% set case = var('sim_case') %}
  {% set ids = ['VIEW_ID', 'SESSION_IDENTIFIER', 'EVENT_ID', 'DOMAIN_SESSIONID', 'SESSION_ID'] %}
  {% set tables = [
    ('snowplow_manifest', 'snowplow_unified_base_sessions_lifecycle_manifest'),
    ('snowplow_manifest', 'snowplow_unified_base_quarantined_sessions'),
    ('derived', 'snowplow_unified_sessions'),
    ('derived', 'snowplow_unified_views'),
  ] %}
  {% for schema, name in tables %}
    {% set rel = api.Relation.create(database=target.database, schema=target.schema ~ '_' ~ case ~ '_' ~ schema, identifier=name) %}
    {% set cols = adapter.get_columns_in_relation(rel) %}
    {% set shifted = [] %}
    {% for c in cols %}
      {% if 'TIMESTAMP' in c.dtype | upper %}
        {% do shifted.append('dateadd(day, -' ~ period_days ~ ' * g.sim_k, t.' ~ c.name ~ ')') %}
      {% elif c.name | upper in ids %}
        {% do shifted.append('t.' ~ c.name ~ " || '_h' || g.sim_k") %}
      {% else %}
        {% do shifted.append('t.' ~ c.name) %}
      {% endif %}
    {% endfor %}
    {% set names = cols | map(attribute='name') | list %}
    {% set has_start = 'START_TSTAMP' in names | map('upper') | list %}
    {% set sql %}
create or replace table {{ rel }} as
select * from (
    select {{ names | join(', ') }} from {{ rel }}
    union all
    select {{ shifted | join(', ') }}
    from {{ rel }} t, (select seq4() + 1 as sim_k from table(generator(rowcount => {{ copies }}))) g
)
{% if has_start %}order by start_tstamp{% endif %}
    {% endset %}
    {% do run_query(sql) %}
    {% do log('inflated ' ~ rel, info=True) %}
  {% endfor %}
  {% set users = target.database ~ '.' ~ target.schema ~ '_' ~ case ~ '_derived.snowplow_unified_users' %}
  {% do run_query('update ' ~ users ~ ' set start_tstamp = dateadd(day, -' ~ copies * period_days ~ ', start_tstamp)') %}
  {% do run_query('create or replace table ' ~ users ~ ' as select * from ' ~ users ~ ' order by start_tstamp') %}
  {% do log('backdated ' ~ users, info=True) %}
{% endmacro %}

{#
  Scores the current case. Truth is the raw events: every human page view
  that was loaded after the seed (seed_now) and before the last run
  (sim_now), up to the last run's upper limit, should be a row in views
  (view_id = event_id). Misses are bucketed by the property that explains them.
#}
{% macro sim_eval(seed_now) %}
  {% set case = var('sim_case') %}
  {% set pre = target.database ~ '.' ~ target.schema ~ '_' ~ case %}
  {% set raw = var('snowplow_raw_events') %}
  {% set accuracy %}
with lim as (
    select max(upper_limit) as upper_limit from {{ pre }}_scratch.snowplow_unified_base_new_event_limits
),
sess as (
    select domain_sessionid, min(collector_tstamp) as sess_start, boolor_agg(useragent ilike '%bot%') as is_bot
    from {{ raw }} group by 1
),
expected as (
    select r.event_id, r.collector_tstamp, r.load_tstamp, r.dvce_created_tstamp, r.dvce_sent_tstamp, s.sess_start, r.domain_sessionid
    from {{ raw }} r join sess s using (domain_sessionid)
    where r.event_name = 'page_view' and not s.is_bot
      and r.load_tstamp >= '{{ seed_now }}'::timestamp_ntz and r.load_tstamp < '{{ var('sim_now') }}'::timestamp_ntz
      and r.collector_tstamp <= (select upper_limit from lim)
),
scored as (
    select e.*, v.view_id is not null as captured, q.session_identifier is not null as quarantined
    from expected e
    left join {{ pre }}_derived.snowplow_unified_views v on v.view_id = e.event_id
    left join (select distinct session_identifier from {{ pre }}_snowplow_manifest.snowplow_unified_base_quarantined_sessions) q
        on q.session_identifier = e.domain_sessionid
)
select
    case when captured then 'captured' else 'missed' end as outcome,
    case when datediff(minute, collector_tstamp, load_tstamp) > 360 then 'load>6h'
         when datediff(minute, collector_tstamp, load_tstamp) > 60 then 'load1-6h' else 'load<1h' end as load_lag,
    case when datediff(minute, dvce_created_tstamp, dvce_sent_tstamp) > 1440 then 'held>1d'
         when datediff(minute, dvce_created_tstamp, dvce_sent_tstamp) > 60 then 'held1-24h' else 'held<1h' end as device_held,
    case when datediff(minute, sess_start, collector_tstamp) > 1440 then 'age>1d' else 'age<1d' end as session_age,
    quarantined,
    count(*) as page_views
from scored
group by all
order by all
  {% endset %}
  {% do sim_print('accuracy ' ~ case, accuracy) %}

  {% set sessions %}
with lim as (
    select max(upper_limit) as upper_limit from {{ pre }}_scratch.snowplow_unified_base_new_event_limits
),
truth as (
    select domain_sessionid, count(*) as n_raw
    from {{ raw }}
    where load_tstamp < '{{ var('sim_now') }}'::timestamp_ntz and collector_tstamp <= (select upper_limit from lim)
    group by 1
    having max(load_tstamp) >= '{{ seed_now }}'::timestamp_ntz and not boolor_agg(useragent ilike '%bot%')
)
select
    count(*) as sessions_touched,
    count_if(s.session_identifier is null) as sessions_missing,
    count_if(s.total_events < t.n_raw) as sessions_undercounted,
    count_if(s.total_events > t.n_raw) as sessions_overcounted,
    sum(t.n_raw - least(coalesce(s.total_events, 0), t.n_raw)) as events_short
from truth t
left join {{ pre }}_derived.snowplow_unified_sessions s on s.session_identifier = t.domain_sessionid
  {% endset %}
  {% do sim_print('sessions ' ~ case, sessions) %}

  {% set clustering %}
select 'views' as t, parse_json(system$clustering_information('{{ pre }}_derived.snowplow_unified_views', '(to_date(start_tstamp))')):average_depth::float as avg_depth
union all
select 'sessions', parse_json(system$clustering_information('{{ pre }}_derived.snowplow_unified_sessions', '(to_date(start_tstamp))')):average_depth::float
union all
select 'manifest', parse_json(system$clustering_information('{{ pre }}_snowplow_manifest.snowplow_unified_base_sessions_lifecycle_manifest', '(to_date(start_tstamp))')):average_depth::float
  {% endset %}
  {% do sim_print('clustering ' ~ case, clustering) %}
  {% do sim_model_cost([case]) %}
{% endmacro %}
