{{ config(materialized='table') }}

-- One row per order date.
select
    sold_date,
    count(distinct order_number) orders,
    count(distinct bill_cutomer_sk_id) customers,
    sum(quantity) quantity,
    sum(cost) cost,
    sum(cost) / nullif(count(distinct order_number), 0) avg_order_value
from {{ ref('snowflake_orders_staging') }}
group by sold_date
