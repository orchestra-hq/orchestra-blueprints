{{
    config(
        materialized='table',
        engine='ReplacingMergeTree(created_at_utc)',
        order_by='(created_date, operation_type, integration)',
        partition_by='toYYYYMM(created_at_utc)'
    )
}}

with operations as (

    select * from {{ ref('stg_orchestra__operations') }}

),

final as (

    select
        -- ids
        operation_id,
        task_run_id,
        external_id,

        -- attributes
        operation_name,
        operation_status,
        operation_type,
        integration,
        integration_job,

        -- metrics
        rows_affected,
        duration_seconds,

        -- date key
        toDate(created_at_utc) as created_date,

        -- timestamps
        created_at_utc,

        -- status flags
        is_successful,
        is_failed,
        is_skipped,
        has_warning,
        is_cancelled,

        -- operation type flags
        is_ingestion_operation,
        is_transformation_operation,
        is_testing_operation,
        is_deployment_operation,

        -- calculated metrics
        case
            when duration_seconds > 0
                then rows_affected / duration_seconds
        end as rows_per_second,

        duration_seconds / 60.0 as duration_minutes,

        -- dlt metadata
        _dlt_load_id,
        _dlt_id

    from operations

)

select * from final
