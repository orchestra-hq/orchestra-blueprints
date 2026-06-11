select
    a.*,
    sha2(cast(a.order_id as string), 256) as _pk
from {{ ref('orders_raw') }} a
cross join range(1000) r
qualify row_number() over (partition by a.order_id order by r.id) = 1
