{{ config(materialized='view', schema='platform_lineage') }}

-- One row per saved chart, resolved through its explore to the BigQuery table
-- that feeds it. `warehouse_external_id` is null for charts whose explore did
-- not compile; those still become assets, just without an upstream edge.
{% if source_table_exists('platform_lineage_raw', 'lightdash_charts') %}

with charts as (
    select * from {{ source('platform_lineage_raw', 'lightdash_charts') }}
),

explores as (
    select * from {{ ref('stg_lightdash__explores') }}
)

select
    charts.project_uuid,
    charts.chart_uuid,
    charts.chart_name,
    charts.description,
    charts.space_name,
    charts.slug,
    charts.updated_at,
    charts.explore_name,
    explores.warehouse_external_id,
    concat(charts.project_uuid, '.', charts.chart_uuid) as chart_external_id
from charts
left join explores
    on charts.project_uuid = explores.project_uuid
   and charts.explore_name = explores.explore_name
where charts.chart_uuid is not null

{% else %}

select
    cast(null as string) as project_uuid,
    cast(null as string) as chart_uuid,
    cast(null as string) as chart_name,
    cast(null as string) as description,
    cast(null as string) as space_name,
    cast(null as string) as slug,
    cast(null as timestamp) as updated_at,
    cast(null as string) as explore_name,
    cast(null as string) as warehouse_external_id,
    cast(null as string) as chart_external_id
limit 0

{% endif %}
