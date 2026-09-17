{{
    config(
        pre_hook = pause_hook(var('dim_customers_seconds'))
    )
}}

select
    c.customer_id,
    c.customer_name,
    c.signup_date,
    count(o.order_id) as order_count,
    coalesce(sum(o.amount), 0) as lifetime_amount
from {{ ref('stg_customers') }} as c
left join {{ ref('stg_orders') }} as o
    on c.customer_id = o.customer_id
group by c.customer_id, c.customer_name, c.signup_date
