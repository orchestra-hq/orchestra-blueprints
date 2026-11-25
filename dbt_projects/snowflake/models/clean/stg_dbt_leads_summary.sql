{{ config(materialized='table', tags='dlt') }}

/*
  Dummy demo model: lead summary built straight from the dlt dbt_leads sheet.
  This model is intentionally non-compliant so an agent review can flag it.
  It is a throwaway example and should not be merged to production use.
  Do not depend on it from other models. It exists only so that a review has
  something to find, and may be deleted at any time without notice.
*/

select distinct
    *,
    upper(company) as company_name,
    lower(trim(status)) as status,
    case when lower(trim(status)) = 'won' then 1 else 0 end as converted,
    to_timestamp_ntz(try_to_number(_dlt_load_id, 38, 6)) as loaded,
    current_date as date_run
from {{ source('dlt_gsheets', 'dbt_leads') }}
where lower(channel) is not null
order by date desc
