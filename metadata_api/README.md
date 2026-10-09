# Orchestra Metadata -> dlt -> Warehouse

You can easily extract all the metadata from Orchestra into your warehouse. We will be using dlt for this. A [templated pipeline is available to get started](https://app.getorchestra.io/ai-agents/workflows)

1. Copy this `metadata_api` folder to your repo. You will need the `.dlt` folder, `requirements.txt`, and `run.py` files.
2. Create a [Python integration](https://docs.getorchestra.io/docs/integrations/python/) to execute the dlt script. Ensure you have secrets provisioned - they should follow the dlt schema for adding secrets.

## What each run loads

Each run loads the `pipeline_runs`, `task_runs`, and `operations` that changed since the previous successful run, plus a full snapshot of `assets`. The first run loads the last 7 days. Operations are re-read for an extra day, because their cost figures are filled in after they first appear. The end of each run's window is kept in dlt's pipeline state in your destination, so this works even though every Orchestra task starts in a fresh container. A failed run does not move the window on, so the next run picks up where the last successful one ended.

Each run also loads `agent_token_usage`: one row per UTC day with the input and output tokens spent by agent sessions, summed across the whole account (the API does not split it by agent or session). A session's tokens count towards the day it was created, so the last two days are re-read each run. This needs an API token with permission to view account settings; without it, the table is skipped with a warning and the rest of the load carries on.

Pipeline runs and task runs are read only once, however often the pipeline is scheduled. Operations cost more to re-read on a frequent schedule, since every run re-reads their last day: hourly runs read each operation up to 24 times. Schedule it only as often as you need fresh data. If the pipeline does not succeed for more than 7 days, the next run loads the last 7 days only and prints a warning: fill the gap with `--backfill-days`.

## Backfilling history

To load older history, pass `--backfill-days`:

```bash
python run.py snowflake --backfill-days 90
```

This backfills the last 90 days of `pipeline_runs`/`task_runs`/`operations` before running the standard load, and loads `agent_token_usage` for the same period in one request (capped at 366 days). The Orchestra API caps each request's `time_from`/`time_to` window to 7 days (and `time_from` can't be earlier than 2023-01-01), so the script automatically chunks the backfill into consecutive 7-day requests. Every load uses `write_disposition="merge"`, so re-running a backfill (or the standard load) is safe and idempotent.

In the included `orchestra_pipeline.yaml`, this is exposed as the `backfill_days` pipeline input (default `"0"`, meaning no backfill) - set it when triggering a run to backfill on demand.

Examples for Snowflake, BigQuery, MySQL, and MotherDuck are below. Do not forget to add your Orchestra API Token to the `secrets.json` section of the credential as well.

Snowflake:

```json
{
    "DESTINATION__SNOWFLAKE__CREDENTIALS__DATABASE": "DATABASE_NAME",
    "DESTINATION__SNOWFLAKE__CREDENTIALS__PASSWORD": "SOME_PASSWORD",
    "DESTINATION__SNOWFLAKE__CREDENTIALS__USERNAME": "USER_NAME",
    "DESTINATION__SNOWFLAKE__CREDENTIALS__HOST": "SNOWFLAKE_ACCOUNT_IDENTIFIER",
    "DESTINATION__SNOWFLAKE__CREDENTIALS__WAREHOUSE": "SOME_WAREHOUSE",
    "DESTINATION__SNOWFLAKE__CREDENTIALS__ROLE": "ROLE_NAME",
    "ORCHESTRA_API_TOKEN" : "your_api_token"
}
```

MySQL:

```json
{
    "DESTINATION__MSSQL__CREDENTIALS__DATABASE": "master",
    "DESTINATION__MSSQL__CREDENTIALS__USERNAME": "OrchestraAdmin",
    "DESTINATION__MSSQL__CREDENTIALS__PASSWORD": "Orchestra123",
    "DESTINATION__MSSQL__CREDENTIALS__HOST": "orchestra-test-blah.database.windows.net",
    "DESTINATION__MSSQL__CREDENTIALS__PORT": "1433",
    "DESTINATION__MSSQL__CREDENTIALS__CONNECT_TIMEOUT": "15",
    "DESTINATION__MSSQL__CREDENTIALS__QUERY__TRUSTSERVERCERTIFICATE": "yes",
    "DESTINATION__MSSQL__CREDENTIALS__QUERY__ENCRYPT": "yes",
    "DESTINATION__MSSQL__CREDENTIALS__QUERY__LONGASMAX": "yes",
    "ORCHESTRA_API_TOKEN" : "your_api_token"
}
```

BigQuery:

```json
{
    "DESTINATION__BIGQUERY__LOCATION": "US",
    "DESTINATION__BIGQUERY__CREDENTIALS__PROJECT_ID": "orchestrametadatastore",
    "DESTINATION__BIGQUERY__CREDENTIALS__PRIVATE_KEY": "-----BEGIN PRIVATE KEY-----\nALONGSTRING\n-----END PRIVATE KEY-----\n",
    "DESTINATION__BIGQUERY__CREDENTIALS__CLIENT_EMAIL": "someuser@someaccount.iam.gserviceaccount.com",
    "ORCHESTRA_API_TOKEN" : "your_api_token"
}
```

MotherDuck:

Use `motherduck` as the warehouse argument when running `run.py`.

```json
{
    "DESTINATION__MOTHERDUCK__CREDENTIALS": "md:///orchestra_metadata_app?motherduck_token=YOUR_MOTHERDUCK_TOKEN",
    "ORCHESTRA_API_TOKEN" : "your_api_token"
}
```
