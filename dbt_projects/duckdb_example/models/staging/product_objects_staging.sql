{{ config(materialized='view') }}

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
