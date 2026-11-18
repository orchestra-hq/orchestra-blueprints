-- Daily revenue by customer region
with orders as (
    select
        seq4() as order_id,
        uniform(1, 1000, random(1)) as customer_id,
        dateadd(day, -uniform(0, 365, random(2)), current_date) as order_date,
        uniform(5, 500, random(3))::number(10, 2) as amount
    from table(generator(rowcount => 200000))
),

customers as (
    select
        seq4() + 1 as customer_id,
        case mod(seq4(), 4) when 0 then 'EMEA' when 1 then 'AMER' when 2 then 'APAC' else 'LATAM' end as region
    from table(generator(rowcount => 1000))
)

select
    o.order_date,
    c.region,
    count(*) as order_count,
    sum(o.amount) as revenue
from orders o
inner join customers c on o.customer_id = c.customer_id
group by 1, 2
