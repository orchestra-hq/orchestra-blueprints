{{ config(materialized='view', schema='platform_lineage') }}

-- One row per saved chart, resolved through its explore to the BigQuery table
-- that feeds it. `warehouse_external_id` is null for charts whose explore did
-- not compile; those still become assets, just without an upstream edge.
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
