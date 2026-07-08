-- Staging: light cleaning of raw orders
with source as (
    select * from {{ source('main_raw', 'src_orders') }}
)

select
    cast(order_id as bigint)             as order_id,
    cast(customer_id as bigint)          as customer_id,
    cast(order_date as timestamp)        as order_ts,
    cast(order_date as date)             as order_date,
    cast(total_amount as decimal(18, 2)) as total_amount
from source
