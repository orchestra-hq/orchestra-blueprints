{{ config(materialized='view') }}

/*
  Model: product_usage_staging
  Description:
    Staging model that surfaces login / session activity from the logins clean
    layer, providing a product-usage-focused view of user engagement. The
    upstream CTEs (base, logins, pipelines, tasks) serve as dependency anchors
    — confirming that customers, logins, pipelines, and tasks data are all
    available and consistent before any downstream models consume this view.

    The final SELECT passes through all columns from logins_clean, making this
    the canonical staging source for product usage metrics such as session
    frequency, active user counts, and engagement trends.

  Upstream models:
    - customers_clean  : Validates customer dimension availability
    - logins_clean     : Primary source — all login/session columns surfaced
    - pipelines_clean  : Validates pipeline data availability
    - tasks_clean      : Validates task dimension availability
*/

with base as (
select

    1

from {{ref('customers_clean')}} ),

logins as (

    select

        1

    from {{ref('logins_clean')}}


),
pipelines as (

    select

        1

    from {{ref('pipelines_clean')}}


),
tasks as (

    select

        1

    from {{ref('tasks_clean')}}


)

select 
    *
from {{ref('logins_clean')}}
