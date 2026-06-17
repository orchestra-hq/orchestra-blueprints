with source as (

    select * from {{ source('orchestra', 'operations') }}

),

renamed as (

    select
        -- ids
        id as operation_id,
        task_run_id,
        external_id,

        -- attributes
        name as operation_name,
        status as operation_status,
        type as operation_type,
        integration,
        integration_job,

        -- metrics
        rows_affected,
        duration_seconds,

        -- timestamps
        created_at as created_at_utc,

        -- status flags
        status = 'SUCCEEDED' as is_successful,
        status = 'FAILED' as is_failed,
        status = 'SKIPPED' as is_skipped,
        status = 'WARNING' as has_warning,
        status in ('CANCELLED', 'CANCELED', 'CANCELLING', 'CANCELING') as is_cancelled,

        -- operation type flags
        type in ('INGESTION') as is_ingestion_operation,
        type in ('TRANSFORMATION', 'MATERIALISATION', 'MATERIALIZATION', 'REFRESH') as is_transformation_operation,
        type in ('TEST', 'TEST_GROUP') as is_testing_operation,
        type in ('DEPLOY') as is_deployment_operation,

        -- dlt metadata
        _dlt_load_id,
        _dlt_id

    from source

)

select * from renamed
