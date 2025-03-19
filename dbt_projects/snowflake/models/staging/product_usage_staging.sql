{{ config(materialized='view') }}

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
