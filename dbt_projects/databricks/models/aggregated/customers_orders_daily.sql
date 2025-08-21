
with orders as (


select
    a.customer_id,
    b.first_name,
    b.last_name,
    b.email,
    a.order_date,
    count(distinct a.order_id) as orders,
    sum(a.order_amount) as amount
from {{ref('orders')}} a 
left join {{ref('customers')}} b 
    on a.customer_id = b.customer_id
group by 
    a.customer_id,
    b.first_name,
    b.last_name,
    b.email,
    a.order_date

)

select

    a.Day,
    b.*,
    HASHBYTES('SHA2_256', CONCAT(cast(a.Day as NVARCHAR(255)),cast(b.customer_id as NVARCHAR(255)))) _pk




from {{ref('daily_calendar')}} a
left join orders b 
on a.Day = b.order_date
