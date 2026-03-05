/*
  Model: product_usage_aggregated
  Description:
    Aggregated view over product usage events, with the customer dimension
    available as a future join key. Currently the model passes through all
    columns from `product_usage_staging` without transformation.

    The CTEs (base, tasks) are stub references selecting a literal 1 — they
    formalise the intended upstream dependencies and act as placeholders for
    filter or aggregation logic to be added as requirements are defined.

    Intended future enhancements include: rolling-up usage events by customer,
    calculating active-user metrics, and surfacing feature adoption signals for
    downstream reporting and alerting models.

  Sources:
    - clean.customers_clean         (customer dimension — stub)
    - staging.product_usage_staging (product usage events — final output)
  Grain:   one row per product usage event (pass-through from staging)
  Output:  all columns from product_usage_staging
*/
{{ config(materialized='view') }}

with base as (
select

    1

from {{ref('customers_clean')}} ),


tasks as (

    select

        1

    from {{ref('product_usage_staging')}}


)

select 
    *
from {{ref('product_usage_staging')}}
