-- Daily pipeline run KPIs: counts, success rate, and duration metrics
WITH base AS (
  SELECT
    run_date,
    status,
    duration_seconds
  FROM {{ ref('stg_pipeline_runs') }}
),
by_status AS (
  SELECT
    run_date,
    SUM(CASE WHEN lower(status) IN ('success','succeeded','completed') THEN 1 ELSE 0 END) AS num_success,
    SUM(CASE WHEN lower(status) IN ('failed','error') THEN 1 ELSE 0 END) AS num_failed,
    COUNT(*) AS num_total
  FROM base
  GROUP BY 1
),
duration_stats AS (
  SELECT
    run_date,
    COUNT(*)::UBIGINT AS num_with_duration,
    AVG(duration_seconds)::DOUBLE AS avg_duration_seconds,
    MIN(duration_seconds)::BIGINT AS min_duration_seconds,
    MAX(duration_seconds)::BIGINT AS max_duration_seconds,
    approx_quantile(duration_seconds, 0.50) AS p50_duration_seconds,
    approx_quantile(duration_seconds, 0.90) AS p90_duration_seconds
  FROM base
  WHERE duration_seconds IS NOT NULL AND duration_seconds >= 0
  GROUP BY 1
)
SELECT
  b.run_date,
  b.num_total,
  b.num_success,
  b.num_failed,
  CASE WHEN b.num_total > 0 THEN b.num_success::DOUBLE / b.num_total ELSE NULL END AS success_rate,
  d.num_with_duration,
  d.avg_duration_seconds,
  d.min_duration_seconds,
  d.max_duration_seconds,
  d.p50_duration_seconds,
  d.p90_duration_seconds
FROM by_status b
LEFT JOIN duration_stats d USING (run_date)
ORDER BY 1;

