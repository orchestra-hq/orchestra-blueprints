{{ config(materialized='table', schema='prod') }}

with logins as (
    select * from {{ ref('logins_per_day') }}
),
events as (
    select * from {{ ref('events_per_day') }}
)
select
    coalesce(e.event_date, l.event_date) as event_date,
    e.total_events,
    e.unique_users,
    e.total_value,
    l.login_events
from events e
full outer join logins l using (event_date)
order by event_date

