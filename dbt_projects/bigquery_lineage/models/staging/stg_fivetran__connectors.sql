{{ config(materialized='view', schema='platform_lineage') }}

-- A connector plus the warehouse destination of its group. Fivetran writes into
-- `<destination project>.<connector schema>`, so joining the two gives the
-- BigQuery dataset each connector feeds.
{% if source_table_exists('platform_lineage_raw', 'fivetran_connectors') %}

{%- set has_table_col = source_column_exists('platform_lineage_raw', 'fivetran_connectors', 'table') -%}

with connectors as (
    select * from {{ source('platform_lineage_raw', 'fivetran_connectors') }}
),

destinations as (
    select * from {{ source('platform_lineage_raw', 'fivetran_destinations') }}
)

select
    connectors.connector_id,
    connectors.group_id,
    connectors.group_name,
    connectors.service,
    connectors.connector_schema,
    {{ 'connectors.`table`' if has_table_col else 'cast(null as string)' }} as connector_table,
    connectors.setup_state,
    connectors.sync_state,
    connectors.succeeded_at,
    connectors.created_at,
    destinations.service as destination_service,
    destinations.warehouse_project,
    -- Fivetran's `schema` is `dataset` for a single-table connector and
    -- `dataset.table` when the connector writes one named table.
    split(connectors.connector_schema, '.')[safe_offset(0)] as target_dataset,
    coalesce(
        {{ 'connectors.`table`' if has_table_col else 'cast(null as string)' }},
        split(connectors.connector_schema, '.')[safe_offset(1)]
    ) as target_table,
    concat('fivetran.', connectors.group_id, '.', connectors.connector_id)
        as connector_external_id
from connectors
left join destinations
    on connectors.group_id = destinations.group_id
where connectors.connector_id is not null

{% else %}

-- Fivetran metadata has not been landed yet; keep the shape so downstream
-- models still compile.
select
    cast(null as string) as connector_id,
    cast(null as string) as group_id,
    cast(null as string) as group_name,
    cast(null as string) as service,
    cast(null as string) as connector_schema,
    cast(null as string) as connector_table,
    cast(null as string) as setup_state,
    cast(null as string) as sync_state,
    cast(null as timestamp) as succeeded_at,
    cast(null as timestamp) as created_at,
    cast(null as string) as destination_service,
    cast(null as string) as warehouse_project,
    cast(null as string) as target_dataset,
    cast(null as string) as target_table,
    cast(null as string) as connector_external_id
limit 0

{% endif %}
