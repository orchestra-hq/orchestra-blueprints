/*
  Model: marketing_data_aggregated
  Description:
    Aggregated view intended to combine marketing and customer signals
    across multiple clean-layer sources (customers, logins, Google
    Analytics, seed/reference data).

    Current state: the model is wired up as a pure pass-through of
    `ga_data_clean`. The four leading CTEs (`base`, `logins`, `pipelines`,
    `tasks`) each `SELECT 1` from one of the upstream clean models — they
    are not referenced in the final SELECT but force dbt to register
    those tables as upstream dependencies in the DAG. This guarantees the
    clean-layer build runs before this aggregate, which is useful both
    for freshness and for keeping the lineage graph accurate while the
    real join / aggregation logic is still being designed.

    When the full marketing aggregation is implemented, the literal-1
    CTEs should be replaced with real projections and joined into the
    final SELECT (e.g. customer attribution onto GA events, login-based
    engagement metrics, seeded campaign metadata).

  Sources:
    - clean.customers_clean   (customer dimension — dependency stub)
    - clean.logins_clean      (login events — dependency stub)
    - clean.ga_data_clean     (Google Analytics marketing events — primary source)
    - clean.seed_clean        (seed / reference data — dependency stub)
  Materialization: view (cheap to rebuild while logic evolves)
  Grain:   one row per GA event record (pass-through from ga_data_clean)
  Output:  all columns from ga_data_clean (SELECT *)
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
