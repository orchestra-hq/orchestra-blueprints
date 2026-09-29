-- The 50 dummy customers the orders above refer to.
select
    100 + i as customer_id,
    'customer_' || (100 + i)::varchar as customer_name,
    case i % 2 when 0 then 'EU' else 'US' end as region
from range(0, 50) t(i)
