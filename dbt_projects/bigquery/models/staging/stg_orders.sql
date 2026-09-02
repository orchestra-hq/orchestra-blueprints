select
    cast(order_id as int64) as order_id,
    cast(customer_id as int64) as customer_id,
    cast(order_date as date) as order_date,
    lower(status) as status,
    cast(amount as numeric) as amount
from {{ source('raw', 'raw_orders') }}
