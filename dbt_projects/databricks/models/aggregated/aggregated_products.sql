select

a.*
from  {{ref('staging_products')}} a 
LIMIT 10
