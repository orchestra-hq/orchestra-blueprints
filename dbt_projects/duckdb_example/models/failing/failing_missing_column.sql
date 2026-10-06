-- PURPOSEFULLY FAILING MODEL (2 of 3)
-- Failure mode: compile/bind error during `dbt run`.
-- `column_that_does_not_exist` is not present in the `numbers` seed, so DuckDB
-- raises a Binder Error. Use it to test how Orchestra surfaces dbt compilation
-- errors as distinct from runtime errors.

{{ config(materialized='table', schema='failing', tags=['failing_demo']) }}

select
    a,
    column_that_does_not_exist
from {{ ref('numbers') }}
