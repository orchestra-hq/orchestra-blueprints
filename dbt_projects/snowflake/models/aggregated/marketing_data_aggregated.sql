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

    from {{ref('ga_data_clean')}}


),
tasks as (

    select

        1

    from {{ref('seed_clean')}}


)

select 
    *
from {{ref('ga_data_clean')}}
