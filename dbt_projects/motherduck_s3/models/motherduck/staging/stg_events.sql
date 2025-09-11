{{ config(materialized='table', schema='staging') }}

with source as (
    select * from {{ source('raw', 'events') }}
),
typed as (
    select
        cast(event_name as varchar) as event_name,
        cast(time as timestamp) as event_ts,
        cast(Name as varchar) as user_name,
        cast(Number as bigint) as event_value
    from source
)
select * from typed

