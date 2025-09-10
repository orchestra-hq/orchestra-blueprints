-- Daily task run counts by status
WITH base AS (
  SELECT run_date, status FROM {{ ref('stg_task_runs') }}
)
SELECT
  run_date,
  status,
  COUNT(*)::UBIGINT AS run_count
FROM base
GROUP BY 1,2
ORDER BY 1,2;

