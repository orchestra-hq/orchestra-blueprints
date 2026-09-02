select 

  a.*,
  SHA2(cast(a.order_id as STRING), 256) _pk

 from {{source('raw', 'orders_raw')}} a