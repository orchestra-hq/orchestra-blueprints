-- Staging: light cleaning of raw customers
with source as (
    select * from {{ source('main_raw', 'src_customers') }}
)

select
    cast(customer_id as bigint)          as customer_id,
    trim(customer_name)                  as customer_name,
    lower(trim(customer_email))          as customer_email
from source
