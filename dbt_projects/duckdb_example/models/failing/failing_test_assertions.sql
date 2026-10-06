-- PURPOSEFULLY FAILING MODEL (3 of 3)
-- Failure mode: builds cleanly on `dbt run`, then fails on `dbt test`.
-- Every row has a NULL `store_key` and the `store` values are duplicated, so the
-- not_null and unique tests in schema.yml both fail. Use it to test warning vs.
-- failure behaviour and data-quality alerting in Orchestra.

{{ config(materialized='table', schema='failing', tags=['failing_demo']) }}

select
    cast(null as varchar) as store_key,
    'duplicated_store' as store,
    sum(sales) as total_sales
from {{ ref('store_sales') }}

union all

select
    cast(null as varchar) as store_key,
    'duplicated_store' as store,
    sum(sales) * 2 as total_sales
from {{ ref('store_sales') }}
