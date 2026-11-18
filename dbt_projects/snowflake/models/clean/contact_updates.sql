{{ config(materialized='incremental') }}

-- Latest state of each HubSpot contact, loaded incrementally by last-modified time.
select
    vid as contact_id,
    firstname as first_name,
    lastname as last_name,
    company,
    to_timestamp_ntz(try_to_number(lastmodifieddate) / 1000) as last_modified_at
from {{ source('base', 'hubspot_contacts_raw') }}
{% if is_incremental() %}
where to_timestamp_ntz(try_to_number(lastmodifieddate) / 1000) >= (select min(last_modified_at) from {{ this }})
{% endif %}
