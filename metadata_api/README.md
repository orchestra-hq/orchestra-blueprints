# Orchestra Metadata -> dlt -> Warehouse

You can easily extract all the metadata from Orchestra into your warehouse. We will be using dlt for this. A [templated pipeline is available to get started](https://app.getorchestra.io/ai-agents/workflows)

1. Copy this `metadata_api` folder to your repo. You will need the `.dlt` folder, `requirements.txt`, and `run.py` files.
2. Create a [Python integration](https://docs.getorchestra.io/docs/integrations/python/) to execute the dlt script. Ensure you have secrets provisioned - they should follow the dlt schema for adding secrets.

## Backfilling history

By default, `run.py` loads `pipeline_runs`, `task_runs`, and `operations` for the last 7 days (the Orchestra API's default window when no time filter is given), plus a full snapshot of `assets`. To load older history, pass `--backfill-days`:

```bash
python run.py snowflake --backfill-days 90
```

This backfills the last 90 days of `pipeline_runs`/`task_runs`/`operations` before running the standard load. The Orchestra API caps each request's `time_from`/`time_to` window to 7 days (and `time_from` can't be earlier than 2023-01-01), so the script automatically chunks the backfill into consecutive 7-day requests. Every load uses `write_disposition="merge"`, so re-running a backfill (or the standard load) is safe and idempotent.

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
