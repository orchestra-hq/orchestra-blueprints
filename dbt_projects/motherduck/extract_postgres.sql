-- DuckDB -> MotherDuck extraction script
-- Purpose: Attach to Postgres and MotherDuck, mirror core tables, and extract
--          metadata/statistics into MotherDuck tables for downstream dbt models.
-- Run cadence: Daily (idempotent). Uses CREATE OR REPLACE to refresh snapshots.

-- 1) Extensions
INSTALL motherduck;
LOAD motherduck;
INSTALL postgres;
LOAD postgres;

-- 2) Optional performance tuning
SET threads TO 8;

-- 3) Authentication/attachments
-- NOTE: Replace placeholders with your actual values or set via environment.
-- MotherDuck (requires MD token or configured local/CI env)
-- SET motherduck_token='YOUR_MOTHERDUCK_TOKEN'; -- uncomment if needed
ATTACH 'md:your_motherduck_database' AS md; -- e.g. md:org/db_name

-- Postgres (read-only recommended for safety)
-- Example: postgresql://user:pass@host:5432/dbname
ATTACH 'postgresql://USERNAME:PASSWORD@HOST:5432/DATABASE' AS pg (READ_ONLY);

-- 4) Create schemas in MotherDuck if not present
CREATE SCHEMA IF NOT EXISTS md.raw;
CREATE SCHEMA IF NOT EXISTS md.meta;

-- 5) Snapshot/mirror core operational tables from Postgres into MotherDuck raw
--    We use CREATE OR REPLACE for a simple, robust daily refresh.
CREATE OR REPLACE TABLE md.raw.task_runs AS
SELECT *
FROM pg.public.task_runs;

CREATE OR REPLACE TABLE md.raw.pipeline_runs AS
SELECT *
FROM pg.public.pipeline_runs;

-- 6) Extract light metadata and statistics directly from Postgres
--    a) Row counts per relevant table
CREATE OR REPLACE TABLE md.meta.table_row_counts AS
SELECT 'task_runs' AS table_name, COUNT(*)::UBIGINT AS row_count, now() AS extracted_at
FROM pg.public.task_runs
UNION ALL
SELECT 'pipeline_runs' AS table_name, COUNT(*)::UBIGINT AS row_count, now() AS extracted_at
FROM pg.public.pipeline_runs;

--    b) Column-level metadata for the two tables
CREATE OR REPLACE TABLE md.meta.columns_metadata AS
SELECT
  c.table_schema,
  c.table_name,
  c.column_name,
  c.ordinal_position,
  c.data_type,
  c.is_nullable,
  now() AS extracted_at
FROM pg.information_schema.columns c
WHERE c.table_schema = 'public'
  AND c.table_name IN ('task_runs','pipeline_runs')
ORDER BY c.table_name, c.ordinal_position;

--    c) Status distributions (daily) for each table, computed against Postgres
--       These do not assume foreign keys; they only rely on common columns.
--       If columns are missing, adjust as needed.
CREATE OR REPLACE TABLE md.meta.task_run_status_daily AS
SELECT
  CAST(date_trunc('day', COALESCE(t.started_at, t.completed_at, t.updated_at)) AS DATE) AS run_date,
  t.status,
  COUNT(*)::UBIGINT AS run_count,
  now() AS extracted_at
FROM pg.public.task_runs t
GROUP BY 1,2
ORDER BY 1,2;

CREATE OR REPLACE TABLE md.meta.pipeline_run_status_daily AS
SELECT
  CAST(date_trunc('day', COALESCE(p.started_at, p.completed_at, p.updated_at)) AS DATE) AS run_date,
  p.status,
  COUNT(*)::UBIGINT AS run_count,
  now() AS extracted_at
FROM pg.public.pipeline_runs p
GROUP BY 1,2
ORDER BY 1,2;

--    d) Duration statistics (seconds) computed directly from Postgres
CREATE OR REPLACE TABLE md.meta.pipeline_run_duration_stats AS
WITH base AS (
  SELECT
    CAST(date_trunc('day', COALESCE(p.started_at, p.completed_at, p.updated_at)) AS DATE) AS run_date,
    datediff('second', p.started_at, p.completed_at) AS duration_seconds
  FROM pg.public.pipeline_runs p
  WHERE p.started_at IS NOT NULL AND p.completed_at IS NOT NULL
)
SELECT
  run_date,
  COUNT(*)::UBIGINT AS num_runs,
  AVG(duration_seconds)::DOUBLE AS avg_duration_seconds,
  MIN(duration_seconds)::BIGINT AS min_duration_seconds,
  MAX(duration_seconds)::BIGINT AS max_duration_seconds,
  approx_quantile(duration_seconds, 0.50) AS p50_duration_seconds,
  approx_quantile(duration_seconds, 0.90) AS p90_duration_seconds,
  now() AS extracted_at
FROM base
GROUP BY 1
ORDER BY 1;

-- 7) Optional ingestion run log (append-only)
CREATE TABLE IF NOT EXISTS md.meta.ingestion_runs (
  run_id            UUID DEFAULT uuid(),
  run_ts            TIMESTAMP DEFAULT now(),
  source_name       TEXT,
  details           JSON
);

INSERT INTO md.meta.ingestion_runs (source_name, details)
VALUES
  ('postgres/public.task_runs', '{"action":"snapshot","tables":["task_runs","pipeline_runs"]}'),
  ('postgres/public.pipeline_runs', '{"action":"snapshot","tables":["task_runs","pipeline_runs"]}');

-- End of script

