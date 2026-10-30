{#
  TEST ONLY: prints a simulated case's tuning metrics, outputs and per-step
  cost to the run log, since the task log is where these results can be read.
  Window metrics mirror .claude/skills/tune-snowplow-windows/window_metrics.sql
  with the case's table names.
#}
{% macro sim_print(label, sql) %}
  {% set res = run_query(sql) %}
  {% do log('SIM ' ~ label ~ ' :: ' ~ res.column_names | join(', '), info=True) %}
  {% for row in res.rows %}
    {% set vals = [] %}
    {% for v in row %}{% do vals.append(v | string) %}{% endfor %}
    {% do log('SIM ' ~ label ~ ' :: ' ~ vals | join(', '), info=True) %}
  {% endfor %}
{% endmacro %}

{% macro sim_report() %}
  {% set case = var('sim_case') %}
  {% set manifest = target.database ~ '.' ~ target.schema ~ '_' ~ case ~ '_snowplow_manifest' %}
  {% set derived = target.database ~ '.' ~ target.schema ~ '_' ~ case ~ '_derived' %}
  {% set events_sql %}
    select * from {{ var('snowplow_raw_events') }}
    where load_tstamp < '{{ var('sim_now') }}'::timestamp_ntz
  {% endset %}

  {% set window_metrics %}
with events as (
    select collector_tstamp, load_tstamp, dvce_created_tstamp, dvce_sent_tstamp, domain_sessionid
    from ({{ events_sql }})
    where collector_tstamp >= (select dateadd(day, -30, max(collector_tstamp)) from ({{ events_sql }}))
),
sessions as (
    select session_identifier, start_tstamp, end_tstamp
    from {{ manifest }}.snowplow_unified_base_sessions_lifecycle_manifest
),
lateness as (
    select datediff(second, collector_tstamp, load_tstamp) / 3600 as late_hours
    from events where load_tstamp is not null
),
device_lateness as (
    select datediff(second, dvce_created_tstamp, dvce_sent_tstamp) / 3600 as late_hours
    from events where dvce_sent_tstamp is not null
),
session_length as (
    select datediff(second, start_tstamp, end_tstamp) / 86400 as length_days from sessions
),
session_age as (
    select datediff(second, s.start_tstamp, e.collector_tstamp) / 86400 as age_days
    from events e join sessions s on s.session_identifier = e.domain_sessionid
)
select 'events_in_window' as metric, count(*)::float as value from events
union all select 'load_late_hours_p999', approx_percentile(late_hours, 0.999) from lateness
union all select 'load_late_hours_max', max(late_hours) from lateness
union all select 'device_late_hours_p999', approx_percentile(late_hours, 0.999) from device_lateness
union all select 'device_late_hours_max', max(late_hours) from device_lateness
union all select 'events_device_late_over_3d', count_if(late_hours > 72) from device_lateness
union all select 'sessions', count(*) from sessions
union all select 'session_length_days_p999', approx_percentile(length_days, 0.999) from session_length
union all select 'session_length_days_max', max(length_days) from session_length
union all select 'quarantined_sessions', count(*) from {{ manifest }}.snowplow_unified_base_quarantined_sessions
union all select 'session_age_days_p999', approx_percentile(age_days, 0.999) from session_age
union all select 'session_age_days_max', max(age_days) from session_age
order by metric
  {% endset %}
  {% do sim_print('window_metrics', window_metrics) %}

  {% set outputs %}
select
    (select count(*) from ({{ events_sql }})) as source_events,
    (select count(*) from ({{ events_sql }}) where event_name = 'page_view' and useragent not ilike '%bot%') as source_human_page_views,
    (select count(*) from {{ derived }}.snowplow_unified_views) as views,
    (select count(*) from {{ derived }}.snowplow_unified_sessions) as sessions,
    (select count(*) from {{ derived }}.snowplow_unified_users) as users,
    (select sum(total_events) from {{ derived }}.snowplow_unified_sessions) as session_events,
    (select hash_agg(session_identifier, total_events) from {{ derived }}.snowplow_unified_sessions) as sessions_hash
  {% endset %}
  {% do sim_print('outputs', outputs) %}

  {#- dbt v2 doesn't apply +query_tag, so dbt invocations are told apart by
      time: a step is a run of Snowflake sessions that starts after every
      earlier session has ended. The last step is this report. #}
  {% set cost %}
with q as (
    select session_id, start_time, end_time, execution_time, bytes_scanned,
        query_text ilike '%base_events_this_run%' and query_type in ('CREATE_TABLE_AS_SELECT', 'INSERT', 'MERGE') as is_this_run
    from table({{ target.database }}.information_schema.query_history(
        end_time_range_start => dateadd(hour, -24, current_timestamp()), result_limit => 10000))
    where query_text ilike '%public_{{ case }}_%'
),
sessions as (
    select session_id, min(start_time) as first_start, max(end_time) as last_end,
        count(*) as queries, sum(execution_time) as exec_ms, sum(bytes_scanned) as bytes,
        sum(iff(is_this_run, execution_time, 0)) as this_run_ms, sum(iff(is_this_run, bytes_scanned, 0)) as this_run_bytes
    from q group by session_id
),
prior as (
    select *, max(last_end) over (order by first_start rows between unbounded preceding and 1 preceding) as prior_end
    from sessions
),
stepped as (
    select *, conditional_true_event(prior_end is null or first_start > prior_end) over (order by first_start) as step
    from prior
)
select step, min(first_start) as started, datediff(second, min(first_start), max(last_end)) as wall_s,
    sum(queries) as queries, sum(exec_ms) / 1000 as exec_s, sum(bytes) as bytes_scanned,
    sum(this_run_ms) / 1000 as this_run_exec_s, sum(this_run_bytes) as this_run_bytes
from stepped
group by step
order by step
  {% endset %}
  {% do sim_print('cost', cost) %}
{% endmacro %}

{#- Per-model bytes and execution time for each dbt step of the given cases,
    from the last 24 h of query history. Steps are split as in sim_report. #}
{% macro sim_model_cost(cases) %}
  {% for case in cases %}
  {% set sql %}
with q as (
    select session_id, start_time, end_time, execution_time, bytes_scanned,
        lower(regexp_replace(regexp_substr(query_text, 'snowplow_unified_[a-z0-9_]+', 1, 1, 'i'), '__dbt_tmp.*$', '')) as model
    from table({{ target.database }}.information_schema.query_history(
        end_time_range_start => dateadd(hour, -24, current_timestamp()), result_limit => 10000))
    where query_text ilike '%public_{{ case }}_%'
),
sessions as (
    select session_id, min(start_time) as first_start, max(end_time) as last_end from q group by session_id
),
prior as (
    select *, max(last_end) over (order by first_start rows between unbounded preceding and 1 preceding) as prior_end
    from sessions
),
stepped as (
    select session_id, conditional_true_event(prior_end is null or first_start > prior_end) over (order by first_start) as step
    from prior
)
select s.step, q.model, count(*) as queries, round(sum(q.execution_time) / 1000, 1) as exec_s,
    round(sum(q.bytes_scanned) / 1e6) as mb
from q join stepped s using (session_id)
group by 1, 2
having sum(q.bytes_scanned) > 0 or sum(q.execution_time) > 2000
order by 1, mb desc
  {% endset %}
  {% do sim_print('model_cost ' ~ case, sql) %}
  {% endfor %}
{% endmacro %}
