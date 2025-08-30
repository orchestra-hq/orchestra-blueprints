{{ config(materialized='view') }}

with base as (
select

    1

from {{ref('customers_clean')}} ),


tasks as (

    select

        1

    from {{ref('product_objects_staging')}}


)

select 
    *
from {{ref('product_objects_staging')}}
