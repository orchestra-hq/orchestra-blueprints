select
a.*
from  {{ref('staging_customers')}} a
limit 10
