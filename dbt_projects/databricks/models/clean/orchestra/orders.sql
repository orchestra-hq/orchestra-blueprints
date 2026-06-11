with x as (
  SELECT COUNT(*) as moo
  FROM range(100000000)
)
select 

  a.*,
  SHA2(cast(a.order_id as STRING), 256) _pk

 from {{ref('orders_raw')}} a