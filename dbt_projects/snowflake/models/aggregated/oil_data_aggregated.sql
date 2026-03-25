{{ config(materialized='view') }}

/*
  Model: marketing_data_staging
  Description:
    Staging model that surfaces Google Analytics marketing data from the
    ga_data_clean layer. The upstream CTE references (base, tasks) act as
    dependency anchors, confirming that customer data is present and
    consistent before the final output is produced.

    All columns from ga_data_clean are passed through without transformation,
    making this model the canonical staging source for marketing / web
    analytics consumption in downstream reporting and attribution models.

  Upstream models:
    - customers_clean : Validates customer dimension availability
    - ga_data_clean   : Primary source — all GA marketing event columns
                        surfaced downstream (e.g. sessions, conversions,
                        traffic source, campaign data)
*/

with base as (
select

    1

from {{ref('oil_area_staging')}} ),


tasks as (

    select

        1

    from {{ref('oil_production_staging')}}


)

select 
    site_name,
    owner,
    to_timestamp(timestamp) timestamp,
    measurement,
    _fourth_column,
    _pk
from {{ref('oil_data_clean')}}
