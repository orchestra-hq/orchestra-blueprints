{{ config(materialized='table') }}

/*
  Dimension: dim_oil_site
  Grain: one row per conformed oil site.

  Cleans the stray leading bullet ('•') / whitespace noise present in the raw
  Google Sheet so that e.g. '• Half Moon Exploration Company' and
  'Half Moon Exploration Company' collapse to a single site
  (18 raw site strings -> 15 conformed sites).

  site_key is a deterministic surrogate key (sha2 of the cleaned site name)
  used as the foreign key from fct_oil_measurement.
*/

with source as (

    select
        site_name as site_name_raw,
        owner
    from {{ ref('oil_data_clean') }}

),

cleaned as (

    select
        nullif(trim(regexp_replace(site_name_raw, '^[[:space:]•]+', '')), '') as site_name,
        owner
    from source

),

deduplicated as (

    select
        site_name,
        max(owner) as owner
    from cleaned
    where site_name is not null
    group by site_name

)

select
    sha2(site_name, 256) as site_key,
    site_name,
    owner
from deduplicated
