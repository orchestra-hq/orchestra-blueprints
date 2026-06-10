select 

  a.*,
  SHA2(cast(a.customer_id as STRING), 256) _pk

 from {{ref('customers_raw')}} a