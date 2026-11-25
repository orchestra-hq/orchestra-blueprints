{{ config(materialized='table') }}

with days as (
    select dateadd(day, seq4(), '2024-01-01'::date) as order_date
    from table(generator(rowcount => 1200))
)

select
    order_date,
    100 + mod(datediff(day, '2024-01-01'::date, order_date) * 37, 50) as orders
from days
where order_date <= current_date()
  and order_date >= '{{ var("start_date", "2024-01-01") }}'::date
