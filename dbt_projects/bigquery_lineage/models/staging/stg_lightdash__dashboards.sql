{{ config(materialized='view', schema='platform_lineage') }}

{% if source_table_exists('platform_lineage_raw', 'lightdash_dashboards') %}

-- workspace_name is required by Orchestra's asset API for DASHBOARD-type
-- assets; the Lightdash project name is the natural fit.
with dashboards as (
    select * from {{ source('platform_lineage_raw', 'lightdash_dashboards') }}
),

projects as (
    select * from {{ source('platform_lineage_raw', 'lightdash_projects') }}
)

select
    dashboards.project_uuid,
    dashboards.dashboard_uuid,
    dashboards.dashboard_name,
    dashboards.description,
    dashboards.updated_at,
    coalesce(projects.name, dashboards.project_uuid) as workspace_name,
    concat(dashboards.project_uuid, '.', dashboards.dashboard_uuid) as dashboard_external_id
from dashboards
left join projects
    on dashboards.project_uuid = projects.project_uuid
where dashboards.dashboard_uuid is not null

{% else %}

select
    cast(null as string) as project_uuid,
    cast(null as string) as dashboard_uuid,
    cast(null as string) as dashboard_name,
    cast(null as string) as description,
    cast(null as timestamp) as updated_at,
    cast(null as string) as workspace_name,
    cast(null as string) as dashboard_external_id
limit 0

{% endif %}
