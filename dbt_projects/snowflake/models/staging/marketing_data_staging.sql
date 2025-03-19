{{ config(materialized='view') }}

with base as (
select

    1

from {{ref('customers_clean')}} ),


tasks as (

    select

        1

    from {{ref('customers_clean')}}


)

select 
    *
from {{ref('ga_data_clean')}}
