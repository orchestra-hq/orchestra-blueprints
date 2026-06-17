{{
    config(
        materialized='table',
        engine='ReplacingMergeTree(updated_at_utc)',
        order_by='(created_date, pipeline_id)',
        partition_by='toYYYYMM(created_at_utc)'
    )
}}

with pipeline_runs as (

    select * from {{ ref('stg_orchestra__pipeline_runs') }}

),

task_run_stats as (

    select
        pipeline_run_id,
        count(*) as total_tasks,
        sum(case when is_successful then 1 else 0 end) as successful_tasks,
        sum(case when is_failed then 1 else 0 end) as failed_tasks,
        sum(case when is_skipped then 1 else 0 end) as skipped_tasks,
        sum(case when has_warning then 1 else 0 end) as warning_tasks,
        sum(duration_seconds) as total_task_duration_seconds,
        count(distinct integration) as unique_integrations

    from {{ ref('stg_orchestra__task_runs') }}

    group by 1

),

final as (

    select
        -- ids
        pr.pipeline_run_id,
        pr.pipeline_id,

        -- attributes
        pr.pipeline_name,
        pr.run_status,
        pr.triggered_by,
        pr.git_branch,
        pr.git_commit_sha,

        -- timestamps
        pr.created_at_utc,
        pr.started_at_utc,
        pr.updated_at_utc,
        pr.completed_at_utc,

        -- date keys for dimensional analysis
        toDate(pr.created_at_utc) as created_date,
        toDate(pr.started_at_utc) as started_date,
        toDate(pr.completed_at_utc) as completed_date,

        -- pipeline run metrics
        pr.duration_seconds,
        pr.duration_seconds / 60.0 as duration_minutes,

        -- status flags
        pr.is_successful,
        pr.is_failed,
        pr.is_in_progress,
        pr.is_cancelled,
        pr.has_warning,

        -- task aggregates
        coalesce(ts.total_tasks, 0) as total_tasks,
        coalesce(ts.successful_tasks, 0) as successful_tasks,
        coalesce(ts.failed_tasks, 0) as failed_tasks,
        coalesce(ts.skipped_tasks, 0) as skipped_tasks,
        coalesce(ts.warning_tasks, 0) as warning_tasks,
        coalesce(ts.total_task_duration_seconds, 0) as total_task_duration_seconds,
        coalesce(ts.unique_integrations, 0) as unique_integrations,

        -- task success rate
        case
            when coalesce(ts.total_tasks, 0) > 0
                then coalesce(ts.successful_tasks, 0) * 100.0 / ts.total_tasks
        end as task_success_rate_pct,

        -- dlt metadata
        pr._dlt_load_id,
        pr._dlt_id

    from pipeline_runs as pr
    left join task_run_stats as ts on pr.pipeline_run_id = ts.pipeline_run_id

)

select * from final
