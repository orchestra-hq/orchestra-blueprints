select 

  a.*,
  HASHBYTES('SHA2_256', cast(a.order_id as NVARCHAR(255))) _pk

 from {{ref('product_orders')}} a