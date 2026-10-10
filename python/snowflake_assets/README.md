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

Everything is read from environment variables.

| Variable | Required | Purpose |
| --- | --- | --- |
| `ORCHESTRA_API_KEY` | yes | An Orchestra API key with write access. Orchestra Python tasks set it for you. |
| `SNOWFLAKE_ACCOUNT` | yes | Account identifier, e.g. `abc12345.eu-west-1`. Use the same value as on your Orchestra Snowflake connection, because it forms the start of every `externalId`. |
| `SNOWFLAKE_USER` | yes | Snowflake user. |
| `SNOWFLAKE_PRIVATE_KEY` | one of these two | PEM private key for key-pair auth. |
| `SNOWFLAKE_PASSWORD` | one of these two | Password, used when no private key is set. |
| `SNOWFLAKE_PRIVATE_KEY_PASSPHRASE` | no | Passphrase for an encrypted private key. |
| `SNOWFLAKE_ROLE` | no | Role to run the metadata queries as. |
| `SNOWFLAKE_WAREHOUSE` | no | Default for `--warehouse`. |
| `ORCHESTRA_API_BASE` | no | Defaults to `https://app.getorchestra.io/api/engine/public`. |

The role needs `USAGE` on the database and its schemas, and on the warehouse. Lineage
also needs Snowflake Enterprise Edition and access to `SNOWFLAKE.CORE.GET_LINEAGE`.
Without them the script logs a warning and publishes the assets with no lineage.

## Running it

```bash
python collect_snowflake_assets.py --database ANALYTICS --warehouse COMPUTE_WH
```

| Option | Default | Purpose |
| --- | --- | --- |
| `--database` | required | Database to collect. To collect several, run the script once per database. |
| `--warehouse` | `$SNOWFLAKE_WAREHOUSE` | Warehouse to run the metadata queries on. |
| `--asset-types` | `TABLE,VIEW` | Which asset types to collect. |

The metadata API allows 50 requests a minute, so the script spaces its requests
about 1.5 seconds apart and retries a `429` with backoff. A first run over a few
hundred tables takes several minutes. Later runs skip assets that haven't
changed, so they finish faster. Progress is logged every 25 assets, with counts
of assets created, updated, skipped and failed. The script exits non-zero if
any write fails.

To check the publish logic without Snowflake or Orchestra:

```bash
python test_collect_snowflake_assets.py
```

## Scheduling it in Orchestra

Run it as an Orchestra [Python task](https://docs.getorchestra.io/docs/integrations/python).

1. Copy this folder into the repository your Python connection points at.
2. Put the Snowflake variables above in the connection's secret JSON:

   ```json
   {
     "SNOWFLAKE_ACCOUNT": "abc12345.eu-west-1",
     "SNOWFLAKE_USER": "ORCHESTRA_ASSETS",
     "SNOWFLAKE_PRIVATE_KEY": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
     "SNOWFLAKE_ROLE": "ORCHESTRA_ASSETS"
   }
   ```

3. Add a pipeline with a Python task and a schedule. Run one task for each database.

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
             command: python collect_snowflake_assets.py --database ANALYTICS --warehouse COMPUTE_WH
           depends_on: []
           name: Collect ANALYTICS
       depends_on: []
       name: Collect
   schedule:
     - name: Daily at 6am
       cron: 0 6 ? * * *
       timezone: Europe/London
   ```

Any other scheduler works the same way, as long as it sets the environment
variables above.

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
