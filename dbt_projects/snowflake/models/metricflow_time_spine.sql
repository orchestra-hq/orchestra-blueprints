/*
  Model: metricflow_time_spine
  Description:
    Daily date spine required by dbt's MetricFlow semantic layer whenever a
    semantic model declares a time dimension (see snowflake_orders_metrics.yml,
    which uses ship_date as its agg_time_dimension). MetricFlow joins against
    this spine to support time-based metric queries (e.g. grouping, filling
    gaps, date-range filters).

    Generates one row per day from 2000-01-01 through roughly 2060-01-01
    using Snowflake's GENERATOR table function, so no external package
    (e.g. dbt_utils) is required.

  Docs: https://docs.getdbt.com/docs/build/metricflow-time-spine
*/
{{ config(materialized='table') }}

with spine as (
    select
        dateadd(day, seq4(), to_date('2000-01-01')) as date_day
    from table(generator(rowcount => 21916))  -- ~60 years of days
)

select date_day
from spine
