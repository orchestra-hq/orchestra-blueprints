{{ config(materialized='view') }}

/*
  Model: oil_data_aggregated
  Description:
    Aggregated view over oil-field production measurement data. The model
    selects a curated subset of columns from `oil_data_clean` and casts
    the raw `timestamp` value into a proper TIMESTAMP type for downstream
    time-series analysis.

    The leading CTEs (`base`, `tasks`) are stub references that select a
    literal 1 from `oil_area_staging` and `oil_production_staging`. They
    are not used in the final SELECT but exist as explicit dependency
    anchors so that dbt's DAG forces those upstream staging models to be
    built / refreshed before this aggregate is materialised. Real join
    or filter logic against those sources can be slotted in later
    without having to re-introduce the references.

  Sources:
    - staging.oil_area_staging         (oil-field area metadata — dependency stub)
    - staging.oil_production_staging   (production-side data — dependency stub)
    - clean.oil_data_clean             (cleaned sensor / measurement events — primary source)
  Grain:   one row per cleaned measurement record (pass-through from oil_data_clean)
  Output:
    site_name, owner, timestamp (TIMESTAMP), measurement, _fourth_column, _pk
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
