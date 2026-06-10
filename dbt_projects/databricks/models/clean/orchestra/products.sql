select 

  a.*,
  HASHBYTES('SHA2_256', CONCAT(cast(a.order_id as STRING),cast(a.product_id as STRING))) _pk

 from {{ref('product_orders')}} a