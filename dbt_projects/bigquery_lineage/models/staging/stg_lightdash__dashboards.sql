{{ config(materialized='view', schema='platform_lineage') }}

select
    project_uuid,
    dashboard_uuid,
    dashboard_name,
    description,
    updated_at,
    concat(project_uuid, '.', dashboard_uuid) as dashboard_external_id
from {{ source('platform_lineage_raw', 'lightdash_dashboards') }}
where dashboard_uuid is not null
