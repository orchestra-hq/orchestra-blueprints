# Snowflake asset collection

Orchestra is deprecating asset configurations and asset runs. If you used one to
collect Snowflake tables and views into Orchestra on a schedule,
`collect_snowflake_assets.py` does the same job through the public asset API,
on whatever schedule you choose.

On each run it:

1. Reads the tables and views in one Snowflake database from
   `<database>.INFORMATION_SCHEMA.TABLES`, the same query the built-in collector ran.
2. Reads each one's upstream lineage with `SNOWFLAKE.CORE.GET_LINEAGE`.
3. Lists the Snowflake assets Orchestra already has for your account, then creates
   each new asset with `POST /assets` and updates a changed one with
   `PATCH /assets/{id}`. Assets with nothing changed are skipped.
4. Writes the lineage edges with `POST /assets/dependencies`.

It writes no metrics. Assets are matched on `externalId`, which takes the form
`<SNOWFLAKE_ACCOUNT>.<DATABASE>.<SCHEMA>.<TABLE>`, the same as the built-in
collector's. Assets it collected before are updated in place rather than duplicated.

## Setup

You need Python 3.11 or later.

```bash
pip install -r requirements.txt
```

### Auth

The script reads Snowflake credentials from your Orchestra Snowflake connection.
Link it to the Python connection under **Linked connections**, and Orchestra
exports each of its fields as `SNOWFLAKE__<CONNECTION_ID>__<FIELD>`. If one
Snowflake connection is linked, the script uses it. If several are linked, set
`SNOWFLAKE_CONNECTION_ID` to choose one.

The connection's account identifier forms the start of every `externalId`, so
using the same connection the old asset configuration used keeps assets matched.

To run it outside Orchestra, set the same fields as plain variables instead:

| Variable | Required | Purpose |
| --- | --- | --- |
| `SNOWFLAKE_ACCOUNT` | yes | Account identifier, e.g. `abc12345.eu-west-1`. Use the value from your Orchestra Snowflake connection. |
| `SNOWFLAKE_USER` | yes | Snowflake user. |
| `SNOWFLAKE_PRIVATE_KEY` | one of these two | PEM private key for key-pair auth. |
| `SNOWFLAKE_PASSWORD` | one of these two | Password, used when no private key is set. |
| `SNOWFLAKE_PRIVATE_KEY_PASSPHRASE` | no | Passphrase for an encrypted private key. |
| `SNOWFLAKE_ROLE` | no | Role to run the metadata queries as. |
| `SNOWFLAKE_WAREHOUSE` | no | Default for `--warehouse`. |
| `SNOWFLAKE_DATABASE` | no | Default for `--database`. |

The Orchestra side needs:

| Variable | Default | Purpose |
| --- | --- | --- |
| `ORCHESTRA_API_KEY` | set by Orchestra Python tasks | An Orchestra API key with write access. |
| `ORCHESTRA_BASE_URL` | `app.getorchestra.io` | Orchestra host, e.g. `stage.getorchestra.io`. |

The role needs `USAGE` on the database and its schemas, and on the warehouse. Lineage
also needs Snowflake Enterprise Edition and access to `SNOWFLAKE.CORE.GET_LINEAGE`.
Without them the script logs a warning and publishes the assets with no lineage.
Private link connections aren't supported, since the script connects directly.

## Running it

```bash
python collect_snowflake_assets.py --dry-run   # read Snowflake and log, send nothing
python collect_snowflake_assets.py
```

| Option | Default | Purpose |
| --- | --- | --- |
| `--database` | the connection's database | Database to collect. To collect several, run the script once per database. |
| `--warehouse` | the connection's warehouse | Warehouse to run the metadata queries on. |
| `--asset-types` | `TABLE,VIEW` | Which asset types to collect. |
| `--dry-run` | off | Read Snowflake and log what would be written, without calling Orchestra. |

The metadata API allows 50 requests a minute, so the script spaces its requests
about 1.5 seconds apart. It retries a `429`, a `5xx` or a network error with
backoff. A first run over a few hundred tables takes several minutes. Later runs
skip assets that haven't changed, so they finish faster. Progress is logged every
25 assets, with counts of assets created, updated, skipped and failed. The script
exits non-zero if any write fails.

To check the publish logic without Snowflake or Orchestra:

```bash
python test_collect_snowflake_assets.py
```

## Scheduling it in Orchestra

Create a [Python connection](https://docs.getorchestra.io/docs/integrations/python)
pointing at a repository containing this folder, with your Snowflake connection
under **Linked connections**. Then add a pipeline with one Python task per
database and a schedule. Match the cadence of your old asset configuration.

```yaml
version: v1
name: Snowflake asset collection
pipeline:
  collect:
    tasks:
      analytics:
        integration: PYTHON
        integration_job: PYTHON_EXECUTE_SCRIPT
        connection: <your_python_connection>
        parameters:
          package_manager: PIP
          python_version: '3.12'
          source: GIT
          project_dir: python/snowflake_assets
          build_command: pip install -r requirements.txt
          command: python collect_snowflake_assets.py --database ANALYTICS
        depends_on: []
        name: Collect ANALYTICS
    depends_on: []
    name: Collect
schedule:
  - name: Daily at 6am
    cron: 0 6 ? * * *
    timezone: Europe/London
```

Any other scheduler works the same way, as long as it sets the plain variables
above.

## Differences from the built-in collector

- **No usage, query counts or metrics.** The collector read query history to
  work out each asset's usage, but the public API has no field for it.
- **No row counts, byte sizes or column schemas.** The public API doesn't
  accept them.
- **Lineage comes only from `GET_LINEAGE`.** The collector fell back to
  parsing each object's DDL when `GET_LINEAGE` was unavailable, but that needed
  a SQL parser. An edge is written only when its upstream asset is in
  Orchestra, either from this run or from before it.
- **New assets get their created and last-changed times on the second run.**
  `POST /assets` doesn't store them yet, so the next run adds them with a `PATCH`.
- **Nothing is deleted.** A table dropped from Snowflake stays in Orchestra, as
  it did with asset runs. Delete it with `DELETE /assets/{id}` if you need to.
