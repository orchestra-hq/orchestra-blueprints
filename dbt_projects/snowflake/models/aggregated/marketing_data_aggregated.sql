/*
  Model: marketing_data_aggregated
  Description:
    Aggregated view combining marketing and customer data from multiple
    upstream clean-layer sources. This model joins signals from customers,
    logins, Google Analytics (GA) pipeline data, and seed data to provide
    a unified marketing analytics surface.

    The CTEs (base, logins, pipelines, tasks) are currently stub references
    that select a literal 1 — they exist as scaffolding to formalise the
    intended upstream dependencies. The actual aggregation logic and column
    selection should be added here as requirements are clarified.

    The final SELECT currently passes through all columns from `ga_data_clean`,
    acting as a placeholder until the full join/aggregation logic is
    implemented.

  Sources:
    - clean.customers_clean   (customer dimension — stub)
    - clean.logins_clean      (login events — stub)
    - clean.ga_data_clean     (Google Analytics marketing events — final output)
    - clean.seed_clean        (seed/reference data — stub)
  Grain:   one row per GA event record (pass-through from ga_data_clean)
  Output:  all columns from ga_data_clean
*/
{{ config(materialized='view') }}

with base as (
select

    1

from {{ref('customers_clean')}} ),

logins as (

    select

        1

    from {{ref('logins_clean')}}


),
pipelines as (

    select

        1

    from {{ref('ga_data_clean')}}


),
tasks as (

    select

        1

    from {{ref('seed_clean')}}


)

select 
    *
from {{ref('ga_data_clean')}}
