select 

  a.*,
  sha2(cast(a.order_id as string), 256) as _pk

 from {{source('raw', 'orders_raw')}} a