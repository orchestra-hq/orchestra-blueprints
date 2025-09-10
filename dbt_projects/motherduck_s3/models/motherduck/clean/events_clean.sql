{{ config(materialized='table', schema='clean') }}

with base as (
    select * from {{ ref('stg_events') }}
),
filtered as (
    select
        event_name,
        event_ts,
        user_name,
        event_value
    from base
    where event_name is not null
      and event_ts is not null
)
select * from filtered

