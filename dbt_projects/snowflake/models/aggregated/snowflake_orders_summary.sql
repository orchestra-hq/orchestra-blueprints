/*
  Model: snowflake_orders_summary
  Description:
    A single-table customer order summary (mart) built directly from the
    Snowflake sample TPC-DS `catalog_sales` table. Rolls the raw order lines
    up to one row per billing customer, exposing order counts, units and
    wholesale spend alongside the customer's first/last order dates.

    Transformations applied:
      - Julian-day surrogate date key (CS_SOLD_DATE_SK) is converted to a real
        calendar date, matching the convention used in snowflake_orders_clean
        (offset from anchor '1920-01-01' with a 2415020 numeric shift).
      - Source is capped to 100,000 order lines so this stays a fast, cheap
        model to test in CI. Remove/raise the LIMIT for production use.
      - Aggregated to one row per billing customer; a deterministic SHA-256
        surrogate key `_pk` is generated from the customer key.

  Source:  snowflake.catalog_sales  (Snowflake sample / TPC-DS)
  Grain:   one row per billing customer (bill_customer_sk_id)
  Output:  bill_customer_sk_id, order_count, total_quantity,
           total_wholesale_cost, avg_line_cost, first_order_date,
           last_order_date, _pk
*/
{{ config(materialized='table') }}

with order_lines as (

    select
        CS_BILL_CUSTOMER_SK                                      as bill_customer_sk_id,
        CS_ORDER_NUMBER                                          as order_number,
        CS_QUANTITY                                              as quantity,
        CS_WHOLESALE_COST                                        as cost,
        dateadd(day, CS_SOLD_DATE_SK - 2415020, '1920-01-01')   as sold_date
    from {{ source('snowflake', 'catalog_sales') }}
    where CS_BILL_CUSTOMER_SK is not null
    limit 100000

)

select
    bill_customer_sk_id,
    count(distinct order_number)        as order_count,
    sum(quantity)                       as total_quantity,
    round(sum(cost), 2)                 as total_wholesale_cost,
    round(avg(cost), 2)                 as avg_line_cost,
    min(sold_date)                      as first_order_date,
    max(sold_date)                      as last_order_date,
    sha2_binary(bill_customer_sk_id)    as _pk
from order_lines
group by bill_customer_sk_id
