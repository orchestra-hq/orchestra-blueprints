{{ config(materialized='view', schema='platform_lineage') }}

{% if source_table_exists('platform_lineage_raw', 'bigquery_tables') %}

select
    table_catalog as project_id,
    table_schema as dataset_id,
    table_name,
    table_type,
    creation_time,
    concat(table_catalog, '.', table_schema, '.', table_name) as external_id
from {{ source('platform_lineage_raw', 'bigquery_tables') }}
-- dlt's own bookkeeping tables, BigQuery's anonymous result caches, dbt's
-- temp/backup tables from every historical run, and GA4's BigQuery Export
-- (one table per DAY, going back years -- one workspace here alone has 20k+
-- of them) are all noise, not assets anyone wants in a lineage graph. Without
-- this filter a single warehouse can dwarf the Orchestra API's rate limit.
where not starts_with(table_schema, '_')
  and not starts_with(table_name, '_dlt')
  and not regexp_contains(table_name, r'__dbt_tmp_\d+$')
  and not regexp_contains(table_name, r'__dbt_backup_\d+$')
  and not regexp_contains(table_name, r'^events_(intraday_)?\d{8}$')

{% else %}

select
    cast(null as string) as project_id,
    cast(null as string) as dataset_id,
    cast(null as string) as table_name,
    cast(null as string) as table_type,
    cast(null as timestamp) as creation_time,
    cast(null as string) as external_id
limit 0

{% endif %}
