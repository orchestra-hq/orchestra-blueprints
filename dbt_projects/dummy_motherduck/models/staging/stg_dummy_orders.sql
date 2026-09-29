-- Dummy orders, generated inline so the project has no sources to seed or
-- keep fresh. The row count comes from the upstream Python Task's output.
select
    i as order_id,
    100 + (hash(i::varchar) % 50) as customer_id,
    current_date - (hash(i::varchar || 'd') % 30)::int as order_date,
    case hash(i::varchar || 's') % 3
        when 0 then 'completed'
        when 1 then 'pending'
        else 'returned'
    end as status,
    round(5 + (hash(i::varchar || 'a') % 49500) / 100.0, 2) as amount
from range(1, {{ var('dummy_row_count') | int + 1 }}) t(i)
