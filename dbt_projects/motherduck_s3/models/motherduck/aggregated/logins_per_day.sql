{{ config(materialized='table', schema='aggregated') }}

with base as (
    select * from {{ ref('events_clean') }}
),
daily as (
    select
        date_trunc('day', event_ts) as event_date,
        count_if(lower(event_name) = 'login') as login_events,
        count(*) filter (where lower(event_name) = 'login') as login_events_alt
    from base
    group by 1
)
select event_date, coalesce(login_events, login_events_alt) as login_events
from daily
order by event_date

