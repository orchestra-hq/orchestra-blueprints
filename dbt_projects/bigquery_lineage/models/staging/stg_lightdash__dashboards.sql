{{ config(materialized='view', schema='platform_lineage') }}

{% if source_table_exists('platform_lineage_raw', 'lightdash_dashboards') %}

select
    project_uuid,
    dashboard_uuid,
    dashboard_name,
    description,
    updated_at,
    concat(project_uuid, '.', dashboard_uuid) as dashboard_external_id
from {{ source('platform_lineage_raw', 'lightdash_dashboards') }}
where dashboard_uuid is not null

{% else %}

select
    cast(null as string) as project_uuid,
    cast(null as string) as dashboard_uuid,
    cast(null as string) as dashboard_name,
    cast(null as string) as description,
    cast(null as timestamp) as updated_at,
    cast(null as string) as dashboard_external_id
limit 0

{% endif %}
