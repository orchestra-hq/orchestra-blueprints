{{ config(materialized='view') }}

/*
  Model: oil_data_aggregated
  Description:
    Reporting-ready oil production readings for BI (Power BI). Selects the
    business columns from oil_data_clean and casts the sheet's text timestamp
    to a real TIMESTAMP.

    The CTEs below are dependency anchors only. They make dbt build both
    staging views first and do not change the output.

  Upstream models:
    - oil_data_clean         : All selected columns come from this model
    - oil_area_staging       : Dependency anchor only
    - oil_production_staging : Dependency anchor only

  Grain:   one row per site reading
  Output:  site_name, owner, timestamp, measurement, _fourth_column, _pk
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
    site_name_clean,
    owner,
    to_timestamp(timestamp) timestamp,
    measurement_value,
    _fourth_column,
    _pk
from {{ref('oil_data_clean')}}
