{{ config(materialized='table', schema='platform_lineage') }}

-- Directed lineage edges, shaped like the body of Orchestra's
-- `POST /assets/dependencies`. Three kinds of edge stitch the stack together:
--
--   FIVETRAN       connector      -> BigQuery table it lands
--   GCP_BIG_QUERY  BigQuery table -> BigQuery table (from job history, so dbt
--                                    and dlt writes both show up)
--   LIGHTDASH      BigQuery table -> chart built on it
--
-- Adding a platform means adding one more `union all` block with the same four
-- columns; the publisher and the Orchestra API need nothing else.

with fivetran_to_bigquery as (
    select
        connector_external_id as from_external_id,
        concat(warehouse_project, '.', target_dataset, '.', target_table)
            as to_external_id,
        'FIVETRAN' as integration,
        concat('Fivetran connector ', connector_id, ' syncs this table')
            as lineage_detail
    from {{ ref('stg_fivetran__connectors') }}
    where warehouse_project is not null
      and target_dataset is not null
      and target_table is not null
),

bigquery_to_bigquery as (
    select
        from_external_id,
        to_external_id,
        'GCP_BIG_QUERY' as integration,
        'Derived from BigQuery job history (referenced_tables)' as lineage_detail
    from {{ ref('stg_bigquery__edges') }}
),

bigquery_to_lightdash as (
    select
        warehouse_external_id as from_external_id,
        chart_external_id as to_external_id,
        'LIGHTDASH' as integration,
        concat('Lightdash chart built on explore ', explore_name) as lineage_detail
    from {{ ref('stg_lightdash__charts') }}
    where warehouse_external_id is not null
),

unioned as (
    select * from fivetran_to_bigquery
    union all
    select * from bigquery_to_bigquery
    union all
    select * from bigquery_to_lightdash
),

-- Only keep edges where both ends are assets we are publishing, otherwise
-- Orchestra rejects the whole batch for referencing an unknown externalId.
known_assets as (
    select external_id from {{ ref('lineage_assets') }}
)

select distinct
    unioned.from_external_id,
    unioned.to_external_id,
    unioned.integration,
    unioned.lineage_detail
from unioned
inner join known_assets as upstream
    on unioned.from_external_id = upstream.external_id
inner join known_assets as downstream
    on unioned.to_external_id = downstream.external_id
where unioned.from_external_id != unioned.to_external_id
