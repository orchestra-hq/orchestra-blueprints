{{
    config(
        materialized='table',
        engine='ReplacingMergeTree()',
        order_by='(pipeline_id)'
    )
}}

with pipeline_runs as (

    select * from {{ ref('stg_orchestra__pipeline_runs') }}

),

aggregates as (

    select
        pipeline_id,
        pipeline_name,
        count(*) as total_runs,
        sum(case when is_successful then 1 else 0 end) as successful_runs,
        sum(case when is_failed then 1 else 0 end) as failed_runs,
        sum(case when is_cancelled then 1 else 0 end) as cancelled_runs,
        min(created_at_utc) as first_run_at,
        max(completed_at_utc) as last_run_at,
        avg(duration_seconds) as avg_duration_seconds

    from pipeline_runs

    group by pipeline_id, pipeline_name

),

final as (

    select
        -- ids and attributes
        pipeline_id,
        pipeline_name,

        -- execution metrics
        total_runs,
        successful_runs,
        failed_runs,
        cancelled_runs,

        -- calculated rates
        round(successful_runs * 100.0 / total_runs, 2) as success_rate_pct,
        round(failed_runs * 100.0 / total_runs, 2) as failure_rate_pct,

        -- timing metrics
        first_run_at,
        last_run_at,
        avg_duration_seconds,
        round(avg_duration_seconds / 60.0, 2) as avg_duration_minutes

    from aggregates

)

select * from final
