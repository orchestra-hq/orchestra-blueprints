select id, name, amount from {{ ref('stg_edge') }}
