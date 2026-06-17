with source as (

    select * from {{ source('orchestra', 'assets') }}

),

renamed as (

    select
        -- ids
        id as asset_id,
        external_id,

        -- attributes
        name as asset_name,
        type as asset_type,
        integration,
        status as asset_status,

        -- dependencies
        upstream_dependencies,
        downstream_dependencies,

        -- metrics
        row_count,
        size_bytes,
        size_bytes / 1024.0 / 1024.0 / 1024.0 as size_gb,

        -- timestamps
        created_at as created_at_utc,

        -- asset type flags
        type in ('TABLE', 'VIEW', 'MATERIALIZED_VIEW') as is_database_object,
        type in ('CHART', 'DASHBOARD', 'DASHBOARD_VIEWS', 'WORKBOOK') as is_bi_asset,
        type in ('QUERIES', 'DATASET') as is_query_asset,

        -- dlt metadata
        _dlt_load_id,
        _dlt_id

    from source

)

select * from renamed
