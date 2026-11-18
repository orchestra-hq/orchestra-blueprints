select
    order_date,
    count(*) as order_count,
    countif(status = 'completed') as completed_order_count,
    sum(amount) as gross_amount,
    sum(if(status = 'completed', amount, 0)) as net_amount
from {{ ref('stg_orders') }}
group by order_date
