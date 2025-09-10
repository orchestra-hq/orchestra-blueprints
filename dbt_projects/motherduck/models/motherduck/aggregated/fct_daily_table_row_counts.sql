-- Daily snapshot of table row counts for mirrored raw tables
SELECT
  CAST(date_trunc('day', extracted_at) AS DATE) AS run_date,
  table_name,
  MAX(row_count) AS row_count
FROM {{ source('md_meta', 'table_row_counts') }}
GROUP BY 1,2
ORDER BY 1,2;

