{{ config(materialized='view') }}

/*
  Model: oil_area_staging
  Description:
    Staging view of oil readings for area-level reporting, one row per site reading. Passes oil_data_clean through unchanged; area roll-ups happen downstream.

    The CTEs below are dependency anchors only. They make dbt build
    customers_clean and oil_data_clean before this view and do not change
    the output.

  Upstream models:
    - oil_data_clean  : All columns are selected from this model
    - customers_clean : Dependency anchor only (customer data must be built first)

  Grain:  one row per site reading (same as oil_data_clean)
*/

with base as (
select

    1

from {{ref('customers_clean')}} ),


tasks as (

    select

        1

    from {{ref('oil_data_clean')}}


)

select 
    *
from {{ref('oil_data_clean')}}
