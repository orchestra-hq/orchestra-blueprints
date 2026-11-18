select
    order_date,
    count(*) as order_count,
    sum(order_amount) as order_amount
from {{ ref('orders_staging') }}
group by order_date
