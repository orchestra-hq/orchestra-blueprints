{{
    config(
        materialized='table',
        engine='ReplacingMergeTree()',
        order_by='(asset_id)'
    )
}}

with assets as (

    select * from {{ ref('stg_orchestra__assets') }}

),

final as (

    select
        -- ids and attributes
        asset_id,
        external_id,
        asset_name,
        asset_type,
        integration,
        asset_status,

        -- asset classification flags
        is_database_object,
        is_bi_asset,
        is_query_asset,

        -- dependency counts
        arrayLength(upstream_dependencies) as upstream_dependency_count,
        arrayLength(downstream_dependencies) as downstream_dependency_count,

        -- size and row metrics
        row_count,
        size_bytes,
        size_gb,
        round(size_gb, 2) as size_gb_rounded,

        -- timestamps
        created_at_utc

    from assets

)

select * from final
