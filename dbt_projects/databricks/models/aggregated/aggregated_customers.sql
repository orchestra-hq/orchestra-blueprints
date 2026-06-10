select

a.*
from  {{ref('staging_customers')}} a
LIMIT 10
