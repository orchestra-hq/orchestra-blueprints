select * from {{ ref('stg_edge') }} where amount < 0
