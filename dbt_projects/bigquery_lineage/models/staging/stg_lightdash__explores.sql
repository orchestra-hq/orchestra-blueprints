{{ config(materialized='view', schema='platform_lineage') }}

-- Explores are the join between a Lightdash chart and the warehouse table it
-- reads. Only explores that resolved to a real table are useful for lineage.
{% if source_table_exists('platform_lineage_raw', 'lightdash_explores') %}

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

{% else %}

select
    cast(null as string) as project_uuid,
    cast(null as string) as explore_name,
    cast(null as string) as explore_label,
    cast(null as string) as base_table,
    cast(null as string) as warehouse_database,
    cast(null as string) as warehouse_schema,
    cast(null as string) as warehouse_table,
    cast(null as string) as warehouse_external_id
limit 0

{% endif %}
