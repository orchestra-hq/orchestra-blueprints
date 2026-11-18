-- Daily event load; a full refresh rebuilds the last 60 days.
{{ config(materialized='incremental', unique_key='event_id', incremental_strategy='merge') }}

{% set days = 1 if is_incremental() else 60 %}

with generated as (
    select seq8() as n
    from table(generator(rowcount => {{ days * 500000 }}))
)

select
    md5(to_varchar(n) || to_varchar(current_date)) as event_id,
    dateadd(day, -mod(n, {{ days }}), current_date) as event_date,
    sha2(to_varchar(n), 512) as payload_hash,
    uniform(1, 1000, random()) as amount
from generated
