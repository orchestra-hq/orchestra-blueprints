{{ config(materialized='table', schema='aggregated') }}

with base as (
    select * from {{ ref('events_clean') }}
)
select
    date_trunc('day', event_ts) as event_date,
    count(*) as total_events,
    count(distinct user_name) as unique_users,
    sum(event_value) as total_value
from base
group by 1
order by event_date

