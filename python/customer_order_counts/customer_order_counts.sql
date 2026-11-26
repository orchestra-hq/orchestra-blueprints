select
    c.customer_id,
    c.name,
    a.city as billing_city,
    count(o.order_id) as order_count,
    sum(o.amount) as order_value
from customers c
join addresses a on a.customer_id = c.customer_id
left join orders o on o.customer_id = c.customer_id
group by c.customer_id, c.name, a.city
order by c.customer_id
