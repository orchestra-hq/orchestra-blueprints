{{
    config(
        materialized='table',
        engine='ReplacingMergeTree()',
        order_by='(integration, integration_job)'
    )
}}

with task_runs as (

    select * from {{ ref('stg_orchestra__task_runs') }}

),

operations as (

    select * from {{ ref('stg_orchestra__operations') }}

),

task_aggregates as (

    select
        integration,
        integration_job,
        count(*) as total_task_runs,
        sum(case when is_successful then 1 else 0 end) as successful_task_runs,
        sum(case when is_failed then 1 else 0 end) as failed_task_runs

    from task_runs

    group by integration, integration_job

),

operation_aggregates as (

    select
        integration,
        integration_job,
        count(*) as total_operations,
        sum(rows_affected) as total_rows_affected,
        sum(duration_seconds) as total_operation_duration_seconds,
        avg(rows_affected) as avg_rows_affected

    from operations

    group by integration, integration_job

),

final as (

    select
        -- ids
        ta.integration,
        ta.integration_job,
        ta.integration || '_' || ta.integration_job as integration_key,

        -- task metrics
        total_task_runs,
        successful_task_runs,
        failed_task_runs,
        round(successful_task_runs * 100.0 / total_task_runs, 2) as task_success_rate_pct,

        -- operation metrics
        coalesce(oa.total_operations, 0) as total_operations,
        coalesce(oa.total_rows_affected, 0) as total_rows_affected,
        coalesce(oa.total_operation_duration_seconds, 0) as total_operation_duration_seconds,
        coalesce(oa.avg_rows_affected, 0) as avg_rows_affected

    from task_aggregates as ta
    left join operation_aggregates as oa
        on ta.integration = oa.integration
        and ta.integration_job = oa.integration_job

)

select * from final
