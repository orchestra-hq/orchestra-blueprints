select name, count(*) as order_COUNT, sum(amount) total_amount from {{ ref('stg_orders') }} group by 1
