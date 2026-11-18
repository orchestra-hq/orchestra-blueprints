{{ config(materialized='table') }}

-- One row per site: reading count and measurement range.
select
    site_name,
    count(*) as reading_count,
    min(measurement) as min_measurement,
    max(measurement) as max_measurement,
    max(timestamp) as last_reading_at
from {{ ref('oil_data_claen') }}
group by site_name
