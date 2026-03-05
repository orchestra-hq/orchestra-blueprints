/*
  Model: product_objects_aggregated
  Description:
    Aggregated view over product objects data, joining the customer dimension
    as a future cross-reference. Currently the model passes through all columns
    from `product_objects_staging` without transformation.

    The CTEs (base, tasks) are stub references selecting a literal 1 — they
    formalise the intended upstream dependencies and act as placeholders for
    filter or join logic to be added as requirements are defined.

    Transformation logic such as deduplication, type casting, and customer
    attribution should be implemented here before this model is used in
    production reporting.

  Sources:
    - clean.customers_clean          (customer dimension — stub)
    - staging.product_objects_staging (product object records — final output)
  Grain:   one row per product object record (pass-through from staging)
  Output:  all columns from product_objects_staging
*/
{{ config(materialized='view') }}

with base as (
select

    1

from {{ref('customers_clean')}} ),


tasks as (

    select

        1

    from {{ref('product_objects_staging')}}


)

select 
    *
from {{ref('product_objects_staging')}}
