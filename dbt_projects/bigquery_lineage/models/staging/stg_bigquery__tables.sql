{{ config(materialized='view', schema='platform_lineage') }}

select
    table_catalog as project_id,
    table_schema as dataset_id,
    table_name,
    table_type,
    creation_time,
    concat(table_catalog, '.', table_schema, '.', table_name) as external_id
from {{ source('platform_lineage_raw', 'bigquery_tables') }}
-- dlt's own bookkeeping tables and BigQuery's anonymous result caches are not
-- assets anyone wants to see in a lineage graph.
where not starts_with(table_schema, '_')
  and not starts_with(table_name, '_dlt')
