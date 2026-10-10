# Databricks asset collection

`collect_assets.py` publishes your Databricks Unity Catalog tables and views to
Orchestra's public asset API. Run it on a schedule in place of Orchestra's
built-in Databricks asset configuration.

It runs the same metadata query as the built-in collector
(`system.information_schema.tables`) and builds the same `externalId`,
`<workspace>.<catalog>.<schema>.<table>`. Assets the built-in collector already
created are updated in place, not duplicated. On each run the script:

1. Reads every table and view from Unity Catalog, skipping the `system` and
   `samples` catalogs and `information_schema`.
2. Lists the Databricks assets Orchestra already has for the workspace.
3. Creates new assets (`POST /assets`), updates changed ones
   (`PATCH /assets/{externalId}`) and skips unchanged ones.
4. Reads table-to-table lineage from `system.access.table_lineage` and writes it
   with `POST /assets/dependencies`.

It doesn't write metrics, column-level schemas or asset status, and it never
deletes assets. A table dropped in Databricks stays in Orchestra until you
delete it.

## Setup

```bash
cd python/databricks_assets
pip install -r requirements.txt
```

### Databricks

You need a SQL warehouse and a token for a user or service principal that has:

- `USE CATALOG` on the `system` catalog and `SELECT` on
  `system.information_schema`, which is the same access the built-in collector needs.
- Optionally, `SELECT` on `system.access.table_lineage` for lineage. Without it
  the script logs a warning and publishes assets only.
- `CAN USE` on the SQL warehouse.

The warehouse ID is the last part of the warehouse's HTTP path,
`/sql/1.0/warehouses/<warehouse-id>`.

### Orchestra

Use a [standard API key](https://docs.getorchestra.io/docs/organisation-settings/api-keys).
A read-only key can't create or update assets. The workspace must have the
Metadata API enabled. Orchestra Python tasks set `ORCHESTRA_API_KEY` for you
automatically.

## Configuration

| Flag | Environment variable | Required | Description |
| --- | --- | --- | --- |
| `--host` | `DATABRICKS_HOST` | yes | Workspace host, for example `dbc-1234abcd-5678.cloud.databricks.com` |
| `--warehouse-id` | `DATABRICKS_WAREHOUSE_ID` | yes | SQL warehouse that runs the metadata queries |
| | `DATABRICKS_TOKEN` | yes | Databricks personal access token or service principal token |
| | `ORCHESTRA_API_KEY` | yes | Orchestra API key |
| `--catalog` | `DATABRICKS_CATALOGS` | no | Comma-separated catalogs to collect. Collects every catalog if unset |
| `--asset-types` | `DATABRICKS_ASSET_TYPES` | no | `TABLE`, `VIEW` or both (default `TABLE,VIEW`) |
| `--lineage-days` | `DATABRICKS_LINEAGE_DAYS` | no | Days of lineage history to publish (default `30`). `0` turns lineage off |
| `--dry-run` | | no | Log what would be created or updated without writing anything |
| | `ORCHESTRA_API_BASE` | no | Defaults to `https://app.getorchestra.io/api/engine/public` |

## Running it

```bash
export DATABRICKS_HOST=dbc-1234abcd-5678.cloud.databricks.com
export DATABRICKS_WAREHOUSE_ID=abcdef1234567890
export DATABRICKS_TOKEN=...
export ORCHESTRA_API_KEY=...

python collect_assets.py --dry-run
python collect_assets.py
```

The script logs its progress every 25 assets and ends with created, updated,
skipped and failed counts. It exits non-zero if any write fails.

### Rate limits

Orchestra's metadata API allows 50 requests a minute, so the script waits about
1.5 seconds between calls and retries 429 and 5xx responses with backoff. Every
new or changed asset takes one call, so expect around 40 a minute. The first run
on a large workspace can take a while. Later runs skip unchanged assets and go
much faster. Use `--catalog` to narrow the run if you don't need everything.

## Scheduling it in Orchestra

Run the script as an
[Orchestra Python task](https://docs.getorchestra.io/docs/integrations/python)
on a cron trigger:

1. Create a Python connection to the repository that holds this folder. Add
   `DATABRICKS_TOKEN` to the connection's secrets.
2. Add a pipeline with a single Python task, for example:

```yaml
version: v1
name: Databricks asset collection
pipeline:
  collect:
    tasks:
      collect-databricks-assets:
        integration: PYTHON
        integration_job: PYTHON_EXECUTE_SCRIPT
        parameters:
          package_manager: PIP
          python_version: '3.12'
          build_command: pip install -r requirements.txt
          source: GIT
          command: python collect_assets.py
          project_dir: python/databricks_assets
          shallow_clone_dirs: python/databricks_assets
          environment_variables: '{
            "DATABRICKS_HOST": "dbc-1234abcd-5678.cloud.databricks.com",
            "DATABRICKS_WAREHOUSE_ID": "abcdef1234567890"
            }'
        depends_on: []
        name: Collect Databricks assets
        connection: <your_python_connection>
    depends_on: []
    name: Collect
schedule:
- name: Daily
  cron: 0 6 ? * * *
  timezone: UTC
```

Match the schedule to how often your old asset configuration ran. Once a run
has succeeded, check that your Databricks assets in Orchestra show recent
`updatedAt` timestamps, then turn off the old asset configuration.
