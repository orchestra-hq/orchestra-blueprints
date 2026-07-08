-- Dimension: one row per customer, enriched with order-derived attributes
with customers as (
    select * from {{ ref('stg_src_customers') }}
),

order_rollup as (
    select
        customer_id,
        count(*)                as lifetime_order_count,
        sum(total_amount)       as lifetime_order_value,
        min(order_date)         as first_order_date,
        max(order_date)         as most_recent_order_date
    from {{ ref('stg_src_orders') }}
    group by customer_id
)

select
    c.customer_id,
    c.customer_name,
    c.customer_email,
    split(c.customer_email, '@')[1]                        as email_domain,
    coalesce(o.lifetime_order_count, 0)                    as lifetime_order_count,
    coalesce(o.lifetime_order_value, cast(0 as decimal(18,2))) as lifetime_order_value,
    o.first_order_date,
    o.most_recent_order_date,
    coalesce(o.lifetime_order_count, 0) > 0                as has_ordered
from customers c
left join order_rollup o
    on c.customer_id = o.customer_id
