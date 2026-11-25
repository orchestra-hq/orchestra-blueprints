{{ config(materialized='table') }}

-- One row per order date.
select
    sold_date,
    count(distinct order_number) orders,
    count(distinct bill_cutomer_sk_id) customers,
    sum(quantity) quantity,
    sum(cost) cost
from {{ ref('snowflake_orders_staging') }}
group by sold_date
