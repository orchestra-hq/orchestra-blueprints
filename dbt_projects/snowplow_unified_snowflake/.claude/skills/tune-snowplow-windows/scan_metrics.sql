-- Cost of each Snowplow Unified model per run over the last 14 days.
-- Rows written is the volume measure to compare. Bytes scanned for the
-- *_this_run scratch tables swings with the query plan for the same rows.
-- The stitching post-hook appears as UPDATE queries on stitched_user_id.
-- ACCOUNT_USAGE lags by up to 45 minutes and needs IMPORTED PRIVILEGES on the
-- SNOWFLAKE database.
with q as (
    select
        start_time::date as run_date,
        query_type,
        lower(regexp_replace(regexp_substr(query_text, 'snowplow_unified_[a-z0-9_]+', 1, 1, 'i'), '__dbt_tmp.*$', '')) as model,
        query_type = 'UPDATE' and query_text ilike '%stitched_user_id%' as is_stitching,
        execution_time,
        bytes_scanned,
        rows_produced,
        partitions_scanned,
        partitions_total
    from SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
    where start_time >= dateadd(day, -14, current_timestamp())
      and execution_status = 'SUCCESS'
      and query_text ilike '%snowplow_unified_%'
)
select
    model,
    is_stitching,
    count(distinct run_date) as days,
    round(sum(execution_time) / 1000 / count(distinct run_date), 1) as exec_s_per_day,
    round(sum(bytes_scanned) / 1e9 / count(distinct run_date), 2) as gb_per_day,
    sum(iff(query_type in ('CREATE_TABLE_AS_SELECT', 'INSERT', 'MERGE', 'UPDATE'), rows_produced, 0))
        / count(distinct run_date) as rows_written_per_day,
    sum(partitions_scanned) / nullif(sum(partitions_total), 0) as scan_ratio
from q
where model is not null
group by 1, 2
order by exec_s_per_day desc
