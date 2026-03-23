with model_a as (
    select * from {{ ref('dim_orders') }}
),
snapshot_x as (
    select * from {{ ref('snapshot_x') }}
)

select * from model_a
join snapshot_x on model_a.customer_id = snapshot_x.seed_id
