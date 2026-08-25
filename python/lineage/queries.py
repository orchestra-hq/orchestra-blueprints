"""SQL that shapes the raw dlt tables into Orchestra-ready asset/edge rows.

This runs directly against BigQuery from `publish_lineage.py` -- there is no
intermediate dbt build. Every query already produces exactly the columns
`publish_lineage.py` needs (see `_asset_body` / `publish_edges`), so adding a
platform is one more entry here, the same "one more union all block" idea a
dbt marts model would use, minus the dbt project.

Each entry is `name -> (required_raw_tables, sql)`:

  - `required_raw_tables` lists the raw tables (in `platform_lineage_raw`,
    i.e. `LINEAGE_RAW_DATASET`) the query reads. `publish_lineage.py` skips a
    query outright when any of them have not landed yet -- platforms come
    online at different times (missing credentials, or a run that
    deliberately extracts a subset via the pipeline's `sources` input), and
    one missing table should not fail the whole build.
  - `sql` is a `string.Template` body using `$project` and `$raw_dataset`
    (always available) plus `$table_col` (fivetran only -- see below).

Asset queries must return: external_id, integration, integration_account_id,
asset_name, asset_type, database_name, schema_name, table_name,
workspace_name, description, url, created_in_integration.

Edge queries must return: from_external_id, to_external_id, integration,
lineage_detail.
"""

ASSET_QUERIES = {
    "bigquery_tables": (
        {"bigquery_tables"},
        r"""
        select
          concat(table_catalog, '.', table_schema, '.', table_name) as external_id,
          'GCP_BIG_QUERY' as integration,
          table_catalog as integration_account_id,
          table_name as asset_name,
          if(table_type = 'VIEW', 'VIEW', 'TABLE') as asset_type,
          table_catalog as database_name,
          table_schema as schema_name,
          table_name,
          cast(null as string) as workspace_name,
          cast(null as string) as description,
          cast(null as string) as url,
          safe_cast(creation_time as timestamp) as created_in_integration
        from `$project`.`$raw_dataset`.bigquery_tables
        -- dlt's own bookkeeping tables, dbt's temp/backup tables, and GA4's
        -- BigQuery Export (one table per DAY, 20k+ on the account this was
        -- built against) are noise a lineage graph doesn't want -- and would
        -- blow through Orchestra's rate limit if published.
        where not starts_with(table_schema, '_')
          and not starts_with(table_name, '_dlt')
          and not regexp_contains(table_name, r'__dbt_tmp_\d+$')
          and not regexp_contains(table_name, r'__dbt_backup_\d+$')
          and not regexp_contains(table_name, r'^events_(intraday_)?\d{8}$')
        """,
    ),
    "lightdash_charts": (
        {"lightdash_charts"},
        r"""
        select
          concat(project_uuid, '.', chart_uuid) as external_id,
          'LIGHTDASH' as integration,
          project_uuid as integration_account_id,
          chart_name as asset_name,
          'CHART' as asset_type,
          cast(null as string) as database_name,
          space_name as schema_name,
          cast(null as string) as table_name,
          cast(null as string) as workspace_name,
          description,
          cast(null as string) as url,
          cast(null as timestamp) as created_in_integration
        from `$project`.`$raw_dataset`.lightdash_charts
        where chart_uuid is not null
        """,
    ),
    "lightdash_dashboards": (
        {"lightdash_dashboards", "lightdash_projects"},
        r"""
        select
          concat(d.project_uuid, '.', d.dashboard_uuid) as external_id,
          'LIGHTDASH' as integration,
          d.project_uuid as integration_account_id,
          d.dashboard_name as asset_name,
          'DASHBOARD' as asset_type,
          cast(null as string) as database_name,
          cast(null as string) as schema_name,
          cast(null as string) as table_name,
          -- required by Orchestra's asset API for DASHBOARD-type assets
          coalesce(p.name, d.project_uuid) as workspace_name,
          d.description,
          cast(null as string) as url,
          cast(null as timestamp) as created_in_integration
        from `$project`.`$raw_dataset`.lightdash_dashboards as d
        left join `$project`.`$raw_dataset`.lightdash_projects as p
          on d.project_uuid = p.project_uuid
        where d.dashboard_uuid is not null
        """,
    ),
    "fivetran_connectors": (
        {"fivetran_connectors", "fivetran_destinations"},
        r"""
        select
          concat('fivetran.', c.group_id, '.', c.connector_id) as external_id,
          'FIVETRAN' as integration,
          c.group_id as integration_account_id,
          concat(c.connector_id, ' (', c.service, ' sync)') as asset_name,
          'DATASET' as asset_type,
          dest.warehouse_project as database_name,
          split(c.connector_schema, '.')[safe_offset(0)] as schema_name,
          coalesce($table_col, split(c.connector_schema, '.')[safe_offset(1)]) as table_name,
          cast(null as string) as workspace_name,
          concat(
            'Fivetran ', c.service, " connector '", c.connector_id,
            "' in group ", c.group_name, ' syncing into ', c.connector_schema, '.'
          ) as description,
          cast(null as string) as url,
          safe_cast(c.created_at as timestamp) as created_in_integration
        from `$project`.`$raw_dataset`.fivetran_connectors as c
        left join `$project`.`$raw_dataset`.fivetran_destinations as dest
          on c.group_id = dest.group_id
        where c.connector_id is not null
        """,
    ),
}

EDGE_QUERIES = {
    "fivetran_to_bigquery": (
        {"fivetran_connectors", "fivetran_destinations"},
        r"""
        select
          concat('fivetran.', c.group_id, '.', c.connector_id) as from_external_id,
          concat(
            dest.warehouse_project, '.',
            split(c.connector_schema, '.')[safe_offset(0)], '.',
            coalesce($table_col, split(c.connector_schema, '.')[safe_offset(1)])
          ) as to_external_id,
          'FIVETRAN' as integration,
          concat('Fivetran connector ', c.connector_id, ' syncs this table') as lineage_detail
        from `$project`.`$raw_dataset`.fivetran_connectors as c
        left join `$project`.`$raw_dataset`.fivetran_destinations as dest
          on c.group_id = dest.group_id
        where dest.warehouse_project is not null
          and c.connector_schema is not null
        """,
    ),
    "bigquery_job_history": (
        {"bigquery_job_edges"},
        r"""
        -- Deduplicated job history: the same dbt model rebuilt nightly
        -- produces one job per run but only one edge.
        select distinct
          concat(source_project, '.', source_dataset, '.', source_table) as from_external_id,
          concat(destination_project, '.', destination_dataset, '.', destination_table) as to_external_id,
          'GCP_BIG_QUERY' as integration,
          'Derived from BigQuery job history (referenced_tables)' as lineage_detail
        from `$project`.`$raw_dataset`.bigquery_job_edges
        where source_table is not null
          and destination_table is not null
          and not starts_with(source_dataset, '_')
          and not starts_with(destination_dataset, '_')
          -- A query that reads and writes the same table (an incremental
          -- merge) is not a lineage edge.
          and concat(source_project, '.', source_dataset, '.', source_table)
              != concat(destination_project, '.', destination_dataset, '.', destination_table)
        """,
    ),
    "bigquery_view_refs": (
        {"bigquery_view_refs"},
        r"""
        -- Table -> view edges parsed from the views' own SQL. Overlaps with
        -- bigquery_job_history when both are available (deduped below); this
        -- is the only source when the credential can't list BigQuery jobs.
        select distinct
          concat(source_project, '.', source_dataset, '.', source_table) as from_external_id,
          concat(view_project, '.', view_dataset, '.', view_name) as to_external_id,
          'GCP_BIG_QUERY' as integration,
          'Table referenced by this view\'s SQL' as lineage_detail
        from `$project`.`$raw_dataset`.bigquery_view_refs
        where not starts_with(source_dataset, '_')
          and not starts_with(view_dataset, '_')
          and concat(source_project, '.', source_dataset, '.', source_table)
              != concat(view_project, '.', view_dataset, '.', view_name)
        """,
    ),
    "bigquery_to_lightdash": (
        {"lightdash_charts", "lightdash_explores"},
        r"""
        select
          concat(e.warehouse_database, '.', e.warehouse_schema, '.', e.warehouse_table) as from_external_id,
          concat(c.project_uuid, '.', c.chart_uuid) as to_external_id,
          'LIGHTDASH' as integration,
          concat('Lightdash chart built on explore ', c.explore_name) as lineage_detail
        from `$project`.`$raw_dataset`.lightdash_charts as c
        join `$project`.`$raw_dataset`.lightdash_explores as e
          on c.project_uuid = e.project_uuid
         and c.explore_name = e.explore_name
        where c.chart_uuid is not null
          and e.warehouse_database is not null
          and e.warehouse_schema is not null
          and e.warehouse_table is not null
        """,
    ),
}
