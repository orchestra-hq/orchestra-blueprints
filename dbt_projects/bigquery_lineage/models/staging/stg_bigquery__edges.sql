{{ config(materialized='view', schema='platform_lineage') }}

-- Deduplicate BigQuery's job history into distinct table-to-table edges: the
-- same dbt model rebuilt nightly produces one job per run but only one edge.
select distinct
    concat(source_project, '.', source_dataset, '.', source_table) as from_external_id,
    concat(destination_project, '.', destination_dataset, '.', destination_table)
        as to_external_id
from {{ source('platform_lineage_raw', 'bigquery_job_edges') }}
where source_table is not null
  and destination_table is not null
  and not starts_with(source_dataset, '_')
  and not starts_with(destination_dataset, '_')
  -- A query that reads and writes the same table (an incremental merge) is not
  -- a lineage edge.
  and concat(source_project, '.', source_dataset, '.', source_table)
      != concat(destination_project, '.', destination_dataset, '.', destination_table)
