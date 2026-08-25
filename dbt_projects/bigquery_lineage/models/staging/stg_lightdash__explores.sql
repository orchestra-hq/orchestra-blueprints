{{ config(materialized='view', schema='platform_lineage') }}

-- Explores are the join between a Lightdash chart and the warehouse table it
-- reads. Only explores that resolved to a real table are useful for lineage.
select
    project_uuid,
    explore_name,
    explore_label,
    base_table,
    warehouse_database,
    warehouse_schema,
    warehouse_table,
    concat(warehouse_database, '.', warehouse_schema, '.', warehouse_table)
        as warehouse_external_id
from {{ source('platform_lineage_raw', 'lightdash_explores') }}
where warehouse_database is not null
  and warehouse_schema is not null
  and warehouse_table is not null
