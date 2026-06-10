select 

  a.*,
  HASHBYTES('SHA2_256', cast(a.order_id as STRING)) _pk

 from {{ref('orders_raw')}} a