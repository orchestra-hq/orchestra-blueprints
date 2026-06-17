with source as (

    select * from {{ source('orchestra', 'task_runs') }}

),

renamed as (

    select
        -- ids
        id as task_run_id,
        pipeline_run_id,

        -- attributes
        task_name,
        status as task_status,
        integration,
        integration_job,
        message as status_message,
        external_status,

        -- timestamps
        created_at as created_at_utc,
        started_at as started_at_utc,
        updated_at as updated_at_utc,
        completed_at as completed_at_utc,

        -- calculated fields
        case
            when completed_at is not null and started_at is not null
                then dateDiff('second', started_at, completed_at)
        end as duration_seconds,

        -- status flags
        status = 'SUCCEEDED' as is_successful,
        status = 'FAILED' as is_failed,
        status in ('RUNNING', 'QUEUED', 'CREATED') as is_in_progress,
        status in ('CANCELLED', 'CANCELLING') as is_cancelled,
        status = 'SKIPPED' as is_skipped,
        status = 'WARNING' as has_warning,

        -- dlt metadata
        _dlt_load_id,
        _dlt_id

    from source

)

select * from renamed
