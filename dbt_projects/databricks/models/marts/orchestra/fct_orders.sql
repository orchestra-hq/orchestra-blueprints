-- Fact: one row per order, with ticket-validity measures
with orders as (
    select * from {{ ref('stg_src_orders') }}
),

ticket_rollup as (
    select
        order_id,
        count(*)                                    as ticket_count,
        sum(case when is_valid then 1 else 0 end)   as valid_ticket_count
    from {{ ref('stg_src_tickets') }}
    group by order_id
)

select
    o.order_id,
    o.customer_id,
    o.order_ts,
    o.order_date,
    o.total_amount,
    coalesce(t.ticket_count, 0)                     as ticket_count,
    coalesce(t.valid_ticket_count, 0)               as valid_ticket_count,
    case
        when coalesce(t.ticket_count, 0) = 0 then false
        else t.valid_ticket_count = t.ticket_count
    end                                             as all_tickets_valid
from orders o
left join ticket_rollup t
    on o.order_id = t.order_id
