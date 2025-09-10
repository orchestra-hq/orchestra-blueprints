-- Simple production-facing KPI table joining key daily facts
WITH a AS (
  SELECT * FROM {{ ref('fct_daily_pipeline_kpis') }}
),
b AS (
  SELECT * FROM {{ ref('fct_daily_task_run_statuses') }}
),
c AS (
  SELECT * FROM {{ ref('fct_daily_table_row_counts') }}
)
SELECT
  a.run_date,
  a.num_total AS pipeline_runs_total,
  a.num_success AS pipeline_runs_success,
  a.num_failed AS pipeline_runs_failed,
  a.success_rate,
  a.avg_duration_seconds,
  a.p50_duration_seconds,
  a.p90_duration_seconds,
  SUM(CASE WHEN b.status IS NOT NULL THEN b.run_count ELSE 0 END) AS task_runs_total,
  MAX(CASE WHEN c.table_name = 'task_runs' THEN c.row_count END) AS task_runs_rows,
  MAX(CASE WHEN c.table_name = 'pipeline_runs' THEN c.row_count END) AS pipeline_runs_rows
FROM a
LEFT JOIN b USING (run_date)
LEFT JOIN c USING (run_date)
GROUP BY 1,2,3,4,5,6,7,8
ORDER BY 1;

