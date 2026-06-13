select

    a.order_id,
    a.customer_id,
    a.order_date,
    a.order_amount,
    a.order_status,
    a.payment_method,
    a.shipping_address,
    b.product_id,
    b.product_name,
    b.quantity,
    b.unit_price,
    b.total_price,
    b._pk

from {{ref('orders')}} a 
left join {{ref('products')}} b
cross join range(1000000) r
on a.order_id = b.order_id
qualify row_number() over (partition by b._pk order by r.id) = 1
