{{ config(materialized='view') }}

/*
  Model: oil_production_staging
  Description:
    Staging model that surfaces oil production data from the oil_data_clean
    layer. The upstream CTE references (base, tasks) act as dependency
    anchors, confirming that customer data is available and that
    oil_data_clean has been refreshed before the final output is produced.

    All columns from oil_data_clean are passed through without transformation,
    making this model the canonical staging source for oil production
    metrics (e.g. barrels produced, well-level output, production date
    ranges) consumed by downstream reporting and forecasting models.

  Upstream models:
    - customers_clean : Validates customer dimension availability
    - oil_data_clean  : Primary source — all production columns surfaced
                        downstream (e.g. well id, production volume,
                        production date, field reference)
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
