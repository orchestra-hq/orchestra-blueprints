{{ config(materialized='view') }}

/*
  Model: oil_area_staging
  Description:
    Staging model that surfaces oil-field area-level data from the
    oil_data_clean layer. The upstream CTE references (base, tasks) act as
    dependency anchors, confirming that customer data is present and that
    oil_data_clean is materialized before the final output is produced.

    All columns from oil_data_clean are passed through without transformation,
    making this model the canonical staging source for area-level oil field
    aggregations consumed by downstream production / reservoir reporting
    models.

  Upstream models:
    - customers_clean : Validates customer dimension availability
    - oil_data_clean  : Primary source — all oil-field area columns are
                        surfaced downstream (e.g. area identifiers, basin /
                        field metadata, geospatial attributes)
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
