{{ config(materialized='view', schema='platform_lineage') }}

-- Table -> view edges taken from the views' own SQL. This overlaps with
-- stg_bigquery__edges (job history) where both are available; the union in
-- lineage_edges is de-duplicated, and this one keeps working on a credential
-- that cannot list BigQuery jobs.
select distinct
    concat(source_project, '.', source_dataset, '.', source_table) as from_external_id,
    concat(view_project, '.', view_dataset, '.', view_name) as to_external_id
from {{ source('platform_lineage_raw', 'bigquery_view_refs') }}
where not starts_with(source_dataset, '_')
  and not starts_with(view_dataset, '_')
  and concat(source_project, '.', source_dataset, '.', source_table)
      != concat(view_project, '.', view_dataset, '.', view_name)
