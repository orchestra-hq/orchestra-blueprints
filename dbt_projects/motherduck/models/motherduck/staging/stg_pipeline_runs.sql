-- Staging model for pipeline_runs
-- Assumes columns: id, status, started_at, completed_at, updated_at, created_at
WITH source AS (
  SELECT * FROM {{ source('md_raw', 'pipeline_runs') }}
),
typed AS (
  SELECT
    CAST(id AS VARCHAR)                           AS pipeline_run_id,
    CAST(status AS VARCHAR)                       AS status,
    TRY_CAST(started_at AS TIMESTAMP)             AS started_at,
    TRY_CAST(completed_at AS TIMESTAMP)           AS completed_at,
    TRY_CAST(updated_at AS TIMESTAMP)             AS updated_at,
    TRY_CAST(created_at AS TIMESTAMP)             AS created_at
  FROM source
),
final AS (
  SELECT
    pipeline_run_id,
    status,
    started_at,
    completed_at,
    updated_at,
    created_at,
    datediff('second', started_at, completed_at)  AS duration_seconds,
    CAST(date_trunc('day', COALESCE(started_at, completed_at, updated_at, created_at)) AS DATE) AS run_date
  FROM typed
)
SELECT * FROM final;

