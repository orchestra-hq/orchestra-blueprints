{{ config(materialized='table') }}

with customers as (
    select * from {{ ref('customers_clean') }}
),

logins as (
    select * from {{ ref('logins_clean') }}
),

logins_with_week as (
    select
        l.*,
        date_trunc('week', l.login_timestamp) as week_start,
        yearweek(l.login_timestamp) as year_week
    from logins l
),

logins_by_customer_week as (
    select
        c.customer_id,
        c.customer_name,
        lw.week_start,
        lw.year_week,
        count(*) as total_logins,
        count(distinct lw.login_timestamp) as unique_login_days,
        min(lw.login_timestamp) as first_login_of_week,
        max(lw.login_timestamp) as last_login_of_week
    from logins_with_week lw
    left join customers c
        on lw.customer_id = c.customer_id
    group by 1, 2, 3, 4
)

select
    customer_id,
    customer_name,
    week_start,
    year_week,
    total_logins,
    unique_login_days,
    first_login_of_week,
    last_login_of_week,
    current_timestamp as dbt_created_at
from logins_by_customer_week
order by week_start desc, customer_id
