# Orchestra Metadata -> dlt -> Warehouse

You can easily extract all the metadata from Orchestra into your warehouse. We will be using dlt for this. A [templated pipeline is available to get started](https://app.getorchestra.io/ai-agents/workflows)

1. Copy this `metadata_api` folder to your repo. You will need the `.dlt` folder, `requirements.txt`, and `run.py` files.
2. Create a [Python integration](https://docs.getorchestra.io/docs/integrations/python/) to execute the dlt script. Ensure you have secrets provisioned - they should follow the dlt schema for adding secrets.

An example for Snowflake, BigQuery, and MySQL are below. Do not forget to add your Orchestra API Token to the `secrets.json` section of the credential as well.

Snowflake:

```json
{
    "DESTINATION__SNOWFLAKE__CREDENTIALS__DATABASE": "DATABASE_NAME",
    "DESTINATION__SNOWFLAKE__CREDENTIALS__PASSWORD": "SOME_PASSWORD",
    "DESTINATION__SNOWFLAKE__CREDENTIALS__USERNAME": "USER_NAME",
    "DESTINATION__SNOWFLAKE__CREDENTIALS__HOST": "NOEPBEQ-PQ123456",
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
