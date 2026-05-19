select 

  a.*,
  sha2(CONCAT(cast(a.order_id as STRING),cast(a.product_id as STRING)), 256) _pk

 from {{ref('product_orders')}} a