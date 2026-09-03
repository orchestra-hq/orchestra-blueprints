select
    order_date,
    count(*) as order_count,
    count(*) filter (where status = 'completed') as completed_order_count,
    sum(amount) as gross_amount,
    sum(case when status = 'completed' then amount else 0 end) as net_amount
from {{ ref('stg_orders') }}
group by order_date
