{{ config(materialized='table') }}

/*
  Mart: oil_production_by_site
  Production rolled up per site by joining the fact to dim_oil_site
  (classic star: fct_oil_measurement -> dim_oil_site).
*/

with fct as (

    select * from {{ ref('fct_oil_measurement') }}

),

site as (

    select * from {{ ref('dim_oil_site') }}

)

select
    s.site_key,
    s.site_name,
    s.owner,
    count(*)           as reading_count,
    sum(f.measurement) as total_measurement,
    avg(f.measurement) as avg_measurement,
    min(f.measurement) as min_measurement,
    max(f.measurement) as max_measurement,
    min(f.measured_at) as first_reading_at,
    max(f.measured_at) as last_reading_at
from fct f
join site s on f.site_key = s.site_key
group by 1, 2, 3
