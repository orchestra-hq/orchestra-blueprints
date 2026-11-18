select
    order_date,
    count(*) as order_count,
    count(distinct customer_id) as customer_count,
    sum(order_amount) as order_amount
from {{ ref('orders_staging') }}
group by order_date
