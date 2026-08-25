{{ config(materialized='view', schema='platform_lineage') }}

-- A connector plus the warehouse destination of its group. Fivetran writes into
-- `<destination project>.<connector schema>`, so joining the two gives the
-- BigQuery dataset each connector feeds.
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
    connectors.`table` as connector_table,
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
        connectors.`table`,
        split(connectors.connector_schema, '.')[safe_offset(1)]
    ) as target_table,
    concat('fivetran.', connectors.group_id, '.', connectors.connector_id)
        as connector_external_id
from connectors
left join destinations
    on connectors.group_id = destinations.group_id
where connectors.connector_id is not null
