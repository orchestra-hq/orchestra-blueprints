{{ config(materialized='table') }}

/*
  Mart: oil_production_daily
  Production rolled up per calendar date by joining the fact to dim_oil_date
  (classic star: fct_oil_measurement -> dim_oil_date).
*/

with fct as (

    select * from {{ ref('fct_oil_measurement') }}

),

dim_date as (

    select * from {{ ref('dim_oil_date') }}

)

select
    d.date_key,
    d.calendar_date,
    d.year,
    d.month,
    d.month_name,
    count(*)                   as reading_count,
    count(distinct f.site_key) as active_sites,
    sum(f.measurement)         as total_measurement,
    avg(f.measurement)         as avg_measurement
from fct f
join dim_date d on f.date_key = d.date_key
group by 1, 2, 3, 4, 5
