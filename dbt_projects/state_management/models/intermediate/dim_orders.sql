with orders as (
    select * from {{ ref('stg_orders') }}
),
customers as (
    select * from {{ ref('stg_customers') }}
)
select
    c.*,
    o.*
from orders o
join customers c on o.customer_id = c.customer_id
