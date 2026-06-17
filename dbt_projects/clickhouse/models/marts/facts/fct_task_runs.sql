{{
    config(
        materialized='table',
        engine='ReplacingMergeTree(updated_at_utc)',
        order_by='(created_date, integration)',
        partition_by='toYYYYMM(created_at_utc)'
    )
}}

with task_runs as (

    select * from {{ ref('stg_orchestra__task_runs') }}

),

operation_stats as (

    select
        task_run_id,
        count(*) as total_operations,
        sum(case when is_successful then 1 else 0 end) as successful_operations,
        sum(case when is_failed then 1 else 0 end) as failed_operations,
        sum(case when is_skipped then 1 else 0 end) as skipped_operations,
        sum(rows_affected) as total_rows_affected,
        sum(duration_seconds) as total_operation_duration_seconds,
        count(distinct operation_type) as unique_operation_types

    from {{ ref('stg_orchestra__operations') }}

    group by 1

),

final as (

    select
        -- ids
        tr.task_run_id,
        tr.pipeline_run_id,

        -- attributes
        tr.task_name,
        tr.task_status,
        tr.integration,
        tr.integration_job,
        tr.status_message,
        tr.external_status,

        -- timestamps
        tr.created_at_utc,
        tr.started_at_utc,
        tr.updated_at_utc,
        tr.completed_at_utc,

        -- date keys for dimensional analysis
        toDate(tr.created_at_utc) as created_date,
        toDate(tr.started_at_utc) as started_date,
        toDate(tr.completed_at_utc) as completed_date,

        -- task run metrics
        tr.duration_seconds,
        tr.duration_seconds / 60.0 as duration_minutes,

        -- status flags
        tr.is_successful,
        tr.is_failed,
        tr.is_in_progress,
        tr.is_cancelled,
        tr.is_skipped,
        tr.has_warning,

        -- operation aggregates
        coalesce(os.total_operations, 0) as total_operations,
        coalesce(os.successful_operations, 0) as successful_operations,
        coalesce(os.failed_operations, 0) as failed_operations,
        coalesce(os.skipped_operations, 0) as skipped_operations,
        coalesce(os.total_rows_affected, 0) as total_rows_affected,
        coalesce(os.total_operation_duration_seconds, 0) as total_operation_duration_seconds,
        coalesce(os.unique_operation_types, 0) as unique_operation_types,

        -- operation success rate
        case
            when coalesce(os.total_operations, 0) > 0
                then coalesce(os.successful_operations, 0) * 100.0 / os.total_operations
        end as operation_success_rate_pct,

        -- throughput metrics
        case
            when coalesce(os.total_operation_duration_seconds, 0) > 0
                then coalesce(os.total_rows_affected, 0) / os.total_operation_duration_seconds
        end as rows_per_second,

        -- dlt metadata
        tr._dlt_load_id,
        tr._dlt_id

    from task_runs as tr
    left join operation_stats as os on tr.task_run_id = os.task_run_id

)

select * from final
