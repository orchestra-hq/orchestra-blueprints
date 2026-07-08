-- Staging: light cleaning of raw tickets
with source as (
    select * from {{ source('main_raw', 'src_tickets') }}
)

select
    cast(ticket_uuid as bigint)          as ticket_id,
    cast(order_id as bigint)             as order_id,
    cast(ticket_date as timestamp)       as ticket_ts,
    coalesce(valid, false)               as is_valid
from source
