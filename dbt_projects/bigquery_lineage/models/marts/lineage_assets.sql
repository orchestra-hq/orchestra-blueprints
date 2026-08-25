{{ config(materialized='table', schema='platform_lineage') }}

-- Every asset across every platform, shaped exactly like the body of Orchestra's
-- `POST /assets`. `external_id` follows the convention Orchestra already uses
-- for each integration, so rows here merge with assets Orchestra collected
-- itself rather than duplicating them:
--
--   GCP_BIG_QUERY  <project>.<dataset>.<table>
--   LIGHTDASH      <project_uuid>.<chart_or_dashboard_uuid>
--   FIVETRAN       fivetran.<group_id>.<connector_id>
--
-- Adding a platform means adding one more `union all` block below.

with bigquery_assets as (
    select
        external_id,
        'GCP_BIG_QUERY' as integration,
        project_id as integration_account_id,
        table_name as asset_name,
        case when table_type = 'VIEW' then 'VIEW' else 'TABLE' end as asset_type,
        project_id as database_name,
        dataset_id as schema_name,
        table_name,
        cast(null as string) as description,
        cast(null as string) as url,
        safe_cast(creation_time as timestamp) as created_in_integration
    from {{ ref('stg_bigquery__tables') }}
),

lightdash_charts as (
    select
        chart_external_id as external_id,
        'LIGHTDASH' as integration,
        project_uuid as integration_account_id,
        chart_name as asset_name,
        'CHART' as asset_type,
        cast(null as string) as database_name,
        space_name as schema_name,
        cast(null as string) as table_name,
        description,
        cast(null as string) as url,
        cast(null as timestamp) as created_in_integration
    from {{ ref('stg_lightdash__charts') }}
),

lightdash_dashboards as (
    select
        dashboard_external_id as external_id,
        'LIGHTDASH' as integration,
        project_uuid as integration_account_id,
        dashboard_name as asset_name,
        'DASHBOARD' as asset_type,
        cast(null as string) as database_name,
        cast(null as string) as schema_name,
        cast(null as string) as table_name,
        description,
        cast(null as string) as url,
        cast(null as timestamp) as created_in_integration
    from {{ ref('stg_lightdash__dashboards') }}
),

fivetran_assets as (
    select
        connector_external_id as external_id,
        'FIVETRAN' as integration,
        group_id as integration_account_id,
        concat(connector_id, ' (', service, ' sync)') as asset_name,
        'DATASET' as asset_type,
        warehouse_project as database_name,
        target_dataset as schema_name,
        target_table as table_name,
        concat(
            'Fivetran ', service, " connector '", connector_id,
            "' in group ", group_name, ' syncing into ', connector_schema, '.'
        ) as description,
        cast(null as string) as url,
        safe_cast(created_at as timestamp) as created_in_integration
    from {{ ref('stg_fivetran__connectors') }}
),

unioned as (
    select * from bigquery_assets
    union all
    select * from lightdash_charts
    union all
    select * from lightdash_dashboards
    union all
    select * from fivetran_assets
)

select
    external_id,
    integration,
    integration_account_id,
    asset_name,
    asset_type,
    database_name,
    schema_name,
    table_name,
    description,
    url,
    created_in_integration
from unioned
where external_id is not null
  and asset_name is not null
  and integration_account_id is not null
