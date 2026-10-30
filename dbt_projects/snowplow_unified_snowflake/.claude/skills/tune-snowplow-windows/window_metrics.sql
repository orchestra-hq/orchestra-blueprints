-- One row per measurement behind a Snowplow Unified window var.
-- Measures the last 30 days of events, anchored on the newest event so stale
-- demo data still returns numbers.
-- Tables: the events view the package reads, plus Unified's manifest and
-- quarantine tables. Edit the three names if the target schema changes.
with events as (
    select collector_tstamp, load_tstamp, dvce_created_tstamp, dvce_sent_tstamp, domain_sessionid, useragent
    from SNOWFLAKE_WORKING.SNOWPLOW_ATOMIC_COMPAT.EVENTS
    where collector_tstamp >= (
        select dateadd(day, -30, max(collector_tstamp))
        from SNOWFLAKE_WORKING.SNOWPLOW_ATOMIC_COMPAT.EVENTS
    )
),

sessions as (
    select session_identifier, start_tstamp, end_tstamp
    from SNOWFLAKE_WORKING.PUBLIC_SNOWPLOW_MANIFEST.SNOWPLOW_UNIFIED_BASE_SESSIONS_LIFECYCLE_MANIFEST
),

-- Hours between collection and warehouse load. NULL when the loader doesn't
-- populate load_tstamp. This is what lookback_window_hours has to cover.
lateness as (
    select datediff(second, collector_tstamp, load_tstamp) / 3600 as late_hours
    from events
    where load_tstamp is not null
),

-- Hours a device held an event before sending it. days_late_allowed filters on
-- this (dvce_sent_tstamp vs dvce_created_tstamp), not on load lag.
device_lateness as (
    select datediff(second, dvce_created_tstamp, dvce_sent_tstamp) / 3600 as late_hours
    from events
    where dvce_sent_tstamp is not null
),

-- Human session span from the raw events. The lifecycle manifest caps
-- end_tstamp at start + max_session_days, so it can never show sessions longer
-- than the current setting. Bots run multi-day sessions that should stay
-- quarantined, so they're left out.
session_length as (
    select datediff(second, min(collector_tstamp), max(collector_tstamp)) / 86400 as length_days
    from events
    group by domain_sessionid
    having not coalesce(boolor_agg(useragent ilike '%bot%'), false)
),

-- How old a session already was when each event in the window joined it.
session_age as (
    select datediff(second, s.start_tstamp, e.collector_tstamp) / 86400 as age_days
    from events e
    join sessions s on s.session_identifier = e.domain_sessionid
)

select 'events_in_window' as metric, count(*)::float as value, 'all' as informs from events
union all
select 'events_with_load_tstamp', count(*), 'lookback_window_hours' from lateness
union all
select 'late_hours_p99', approx_percentile(late_hours, 0.99), 'lookback_window_hours' from lateness
union all
select 'late_hours_p999', approx_percentile(late_hours, 0.999), 'lookback_window_hours' from lateness
union all
select 'late_hours_max', max(late_hours), 'lookback_window_hours' from lateness
union all
select 'device_late_hours_p999', approx_percentile(late_hours, 0.999), 'days_late_allowed' from device_lateness
union all
select 'device_late_hours_max', max(late_hours), 'days_late_allowed' from device_lateness
union all
-- Events days_late_allowed = N would drop, for N = 1..7. Read the setting off
-- this curve rather than a percentile: a late tail near 0.1% of events makes
-- p99.9 jump between hours and days from one sample to the next.
select 'device_late_events_over_' || n.n || 'd', count_if(d.late_hours > 24 * n.n), 'days_late_allowed'
from device_lateness d
cross join (select seq4() + 1 as n from table(generator(rowcount => 7))) n
group by n.n
union all
select 'session_length_days_p999', approx_percentile(length_days, 0.999), 'max_session_days' from session_length
union all
select 'session_length_days_max', max(length_days), 'max_session_days' from session_length
union all
select 'quarantined_sessions', count(*), 'max_session_days'
from SNOWFLAKE_WORKING.PUBLIC_SNOWPLOW_MANIFEST.SNOWPLOW_UNIFIED_BASE_QUARANTINED_SESSIONS
union all
select 'session_age_days_p999', approx_percentile(age_days, 0.999), 'session_lookback_days, upsert_lookback_days' from session_age
union all
select 'session_age_days_max', max(age_days), 'session_lookback_days, upsert_lookback_days' from session_age
union all
select 'event_days_in_window', count(distinct collector_tstamp::date), 'backfill_limit_days' from events
order by metric
