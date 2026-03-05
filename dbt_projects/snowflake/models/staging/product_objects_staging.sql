{{ config(materialized='view') }}

/*
  Model: product_objects_staging
  Description:
    Staging model that surfaces login activity from the logins clean layer,
    scoped to the set of customers, pipeline runs, task runs, and tasks that
    exist in the product. The CTE references (base, logins, pipelines, tasks)
    act as dependency anchors — ensuring the upstream clean models are available
    and consistent before the final SELECT is executed.

    The final output is all rows from logins_clean, making this model the
    canonical staging source for login / session activity used in product-object
    level analytics.

  Upstream models:
    - customers_clean      : Validates customer dimension availability
    - pipeline_runs_clean  : Validates pipeline run data availability
    - task_runs_clean      : Validates task run data availability
    - tasks_clean          : Validates task dimension availability
    - logins_clean         : Primary source — all columns surfaced downstream
*/

with base as (
select

    1

from {{ref('customers_clean')}} ),

logins as (

    select

        1

    from {{ref('pipeline_runs_clean')}}


),
pipelines as (

    select

        1

    from {{ref('task_runs_clean')}}


),
tasks as (

    select

        1

    from {{ref('tasks_clean')}}


)

select 
    *
from {{ref('logins_clean')}}
