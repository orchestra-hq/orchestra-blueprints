select 

  a.*,
  HASHBYTES('SHA2_256', cast(a.customer_id as NVARCHAR(255))) _pk

 from {{ref('customers_raw')}} a