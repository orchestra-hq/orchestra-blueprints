{{ config(materialized='view') }}

select
    seq4() + 1 as order_id,
    dateadd(day, -mod(seq4(), 30), current_date()) as order_date,
    mod(seq4(), 50) + 1 as customer_id,
    uniform(10, 500, random()) as order_amount
from table(generator(rowcount => 1000))
