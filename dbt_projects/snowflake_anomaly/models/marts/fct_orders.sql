{{
    config(
        pre_hook = pause_hook(var('fct_orders_seconds'))
    )
}}

-- The pause is the whole point of this model: the aggregate below finishes in
-- well under a second, so the duration Orchestra sees is whatever
-- `fct_orders_seconds` is set to.
select
    order_date,
    count(*) as order_count,
    count_if(status = 'completed') as completed_order_count,
    sum(amount) as gross_amount,
    sum(iff(status = 'completed', amount, 0)) as net_amount
from {{ ref('stg_orders') }}
group by order_date
