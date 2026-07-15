{{ config(materialized='table') }}

/*
  Fact: fct_oil_measurement
  Grain: one row per measurement reading (site + timestamp).

  Foreign keys:
    - site_key -> dim_oil_site.site_key
    - date_key -> dim_oil_date.date_key

  measurement_pk is carried through from oil_data_clean (_pk = sha2 of the raw
  timestamp + raw site_name) and is unique at the reading grain.
*/

with base as (

    select
        _pk,
        nullif(trim(regexp_replace(site_name, '^[[:space:]•]+', '')), '') as site_name,
        try_to_timestamp(timestamp) as measured_at,
        measurement
    from {{ ref('oil_data_clean') }}

)

select
    _pk                                                  as measurement_pk,
    sha2(site_name, 256)                                 as site_key,
    to_number(to_char(to_date(measured_at), 'YYYYMMDD')) as date_key,
    measured_at,
    measurement
from base
where site_name is not null
  and measured_at is not null
