-- PURPOSEFULLY FAILING MODEL (1 of 3)
-- Failure mode: runtime error during `dbt run`.
-- DuckDB raises a Conversion Error when casting a non-numeric literal to INTEGER,
-- so this model never materialises. Use it to test task-level failure handling,
-- alerting and log capture in Orchestra.

{{ config(materialized='table', schema='failing', tags=['failing_demo']) }}

select
    a,
    s,
    cast('not_a_number' as integer) as deliberately_broken_cast
from {{ ref('numbers') }}
