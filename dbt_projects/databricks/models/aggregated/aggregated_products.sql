select
a.*
from  {{ref('staging_products')}} a 
limit 10
