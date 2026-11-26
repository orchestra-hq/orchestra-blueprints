select id, name, amount from {{ ref('raw_orders') }}
