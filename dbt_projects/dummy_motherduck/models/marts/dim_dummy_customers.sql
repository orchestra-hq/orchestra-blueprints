{{
    config(
        pre_hook=spin_hook(var('dim_dummy_customers_seconds'))
    )
}}

-- A second lever, for showing two nodes flagged at once.
select
    c.customer_id,
    c.customer_name,
    c.region,
    count(o.order_id) as order_count,
    coalesce(sum(o.amount), 0) as lifetime_value
from {{ ref('stg_dummy_customers') }} as c
left join {{ ref('stg_dummy_orders') }} as o
    on c.customer_id = o.customer_id
group by 1, 2, 3
