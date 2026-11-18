{{ config(materialized='table') }}

-- Rows landed per day by the dlt Google Sheets loads.
with loads as (
    select 'dbt_leads' as lead_source, to_date(to_timestamp_ntz(try_to_number(_dlt_load_id, 38, 6))) as load_date
    from {{ source('dlt_gsheets', 'dbt_leads') }}
    union all
    select 'social_leads', to_date(to_timestamp_ntz(try_to_number(_dlt_load_id, 38, 6)))
    from {{ source('dlt_gsheets', 'social_leads') }}
),

days as (
    select dateadd(day, row_number() over (order by seq4()) - 1, '2026-09-03'::date) as load_date
    from table(generator(rowcount => 120))
    qualify load_date <= current_date
)

select days.load_date, count(loads.lead_source) as leads_loaded
from days
left join loads on loads.load_date = days.load_date
group by 1
