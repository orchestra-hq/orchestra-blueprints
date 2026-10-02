{{
    config(
        pre_hook=spin_hook(var('fct_dummy_orders_seconds'))
    )
}}

-- The model the demo makes slow, via the spin_hook pre-hook.
select
    o.order_id,
    o.customer_id,
    c.region,
    o.order_date,
    o.status,
    o.amount
from {{ ref('stg_dummy_orders') }} as o
left join {{ ref('stg_dummy_customers') }} as c
    on o.customer_id = c.customer_id
