/*
  Model: store_sales_example
  Description:
    Cleans and aggregates raw store sales data from the `store_sales` seed.

    Cleaning logic:
      - The raw data contains a known bad date value ('05-Nov-2040') used as a
        sentinel/placeholder for missing store information. Rows with this date
        have their `store` field set to NULL so they can be easily filtered or
        handled downstream.

    Aggregation:
      - After cleaning, sales are summed per (store, date) combination so that
        each row represents one store's total revenue for a given day.

  Source:  seeds/store_sales
  Grain:   one row per store per date
  Output:  store, date, sales (aggregated)
*/
with base as (
select

    case when date = '05-Nov-2040' then null else store end as store,
    date,
    sales
from {{ref('store_sales')}}
)

select
    store,
    date,
    sum(sales) sales
from base
group by 1,2
