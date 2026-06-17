with source as (

    select * from {{ source('orchestra', 'pipeline_runs') }}

),

renamed as (

    select
        -- ids
        id as pipeline_run_id,
        pipeline_id,

        -- attributes
        pipeline_name,
        run_status,
        triggered_by,
        branch as git_branch,
        commit as git_commit_sha,

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
        run_status = 'SUCCEEDED' as is_successful,
        run_status = 'FAILED' as is_failed,
        run_status in ('RUNNING', 'CREATED') as is_in_progress,
        run_status in ('CANCELLED', 'CANCELLING') as is_cancelled,
        run_status = 'WARNING' as has_warning,

        -- dlt metadata
        _dlt_load_id,
        _dlt_id

    from source

)

select * from renamed
