{{ config(materialized='table') }}

-- One row per billing customer: lifetime orders, units and spend.
select
    bill_cutomer_sk_id,
    any_value(email) email,
    min(sold_date) first_order_date,
    max(sold_date) last_order_date,
    count(distinct order_number) lifetime_orders,
    sum(quantity) lifetime_quantity,
    sum(cost) lifetime_value,
    current_timestamp() refreshed_at
from {{ ref('snowflake_orders_staging') }}
where bill_cutomer_sk_id is not null
group by bill_cutomer_sk_id
