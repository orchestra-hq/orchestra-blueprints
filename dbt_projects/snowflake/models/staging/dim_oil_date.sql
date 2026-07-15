{{ config(materialized='table') }}

/*
  Dimension: dim_oil_date
  Grain: one row per calendar date on which a measurement was taken.

  The raw `timestamp` column arrives as free text (e.g. '3/23/2026 16:22:01');
  it is parsed with try_to_timestamp and reduced to a date grain. date_key is an
  integer YYYYMMDD surrogate key used as the foreign key from fct_oil_measurement.
*/

with readings as (

    select to_date(try_to_timestamp(timestamp)) as calendar_date
    from {{ ref('oil_data_clean') }}
    where try_to_timestamp(timestamp) is not null

),

dates as (

    select distinct calendar_date
    from readings

)

select
    to_number(to_char(calendar_date, 'YYYYMMDD')) as date_key,
    calendar_date,
    year(calendar_date)       as year,
    quarter(calendar_date)    as quarter,
    month(calendar_date)      as month,
    monthname(calendar_date)  as month_name,
    day(calendar_date)        as day_of_month,
    dayofweek(calendar_date)  as day_of_week,
    dayname(calendar_date)    as day_name,
    weekofyear(calendar_date) as week_of_year
from dates
