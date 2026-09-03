{{ config(alias='stg-orders-clean') }}

select
    cast(order_id as bigint) as order_id,
    cast(customer_id as bigint) as customer_id,
    cast(order_date as date) as order_date,
    lower(status) as status,
    cast(amount as decimal(10, 2)) as amount
from {{ source('raw', 'raw_orders') }}
