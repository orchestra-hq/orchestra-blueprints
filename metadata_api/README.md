# Metadata API

You can easily extract all the metadata from Orchestra into your warehouse.

1. Copy the Metadata_API folder to your repo 
2. Create a [Python integration](https://docs.getorchestra.io/docs/integrations/utility/python/) for your metadata movement, which will execute a dlt script to move data from the Orchestra API to your warehouse
3. Ensure you have secrets provisioned. They should follow the dlt schema for adding secrets. An example for Snowflake and BigQuery, Snowflake and MySQL is below. Do not forget to add your Orchestra API Token to the secrets.json.

```json
{
    "DESTINATION__SNOWFLAKE__CREDENTIALS__DATABASE": "DATABASE_NAME",
    "DESTINATION__SNOWFLAKE__CREDENTIALS__PASSWORD": "SOME_PASSWORD",
    "DESTINATION__SNOWFLAKE__CREDENTIALS__USERNAME": "USER_NAME",
    "DESTINATION__SNOWFLAKE__CREDENTIALS__HOST": "NOEPBEQ-PQ123456",
    "DESTINATION__SNOWFLAKE__CREDENTIALS__WAREHOUSE": "SOME_WAREHOUSE",
    "DESTINATION__SNOWFLAKE__CREDENTIALS__ROLE": "ROLE_NAME",
    "DESTINATION__MSSQL__CREDENTIALS__DATABASE": "master",
    "DESTINATION__MSSQL__CREDENTIALS__USERNAME": "OrchestraAdmin",
    "DESTINATION__MSSQL__CREDENTIALS__PASSWORD": "Orchestra123",
    "DESTINATION__MSSQL__CREDENTIALS__HOST": "orchestra-test-blah.database.windows.net",
    "DESTINATION__MSSQL__CREDENTIALS__PORT": "1433",
    "DESTINATION__MSSQL__CREDENTIALS__CONNECT_TIMEOUT": "15",
    "DESTINATION__MSSQL__CREDENTIALS__QUERY__TRUSTSERVERCERTIFICATE": "yes",
    "DESTINATION__MSSQL__CREDENTIALS__QUERY__ENCRYPT": "yes",
    "DESTINATION__MSSQL__CREDENTIALS__QUERY__LONGASMAX": "yes",
    "DESTINATION__BIGQUERY__LOCATION": "US",
    "DESTINATION__BIGQUERY__CREDENTIALS__PROJECT_ID": "orchestrametadatastore",
    "DESTINATION__BIGQUERY__CREDENTIALS__PRIVATE_KEY": "-----BEGIN PRIVATE KEY-----\nALONGSTRING\n-----END PRIVATE KEY-----\n",
    "DESTINATION__BIGQUERY__CREDENTIALS__CLIENT_EMAIL": "someuser@someaccount.iam.gserviceaccount.com",
    "ORCHESTRA_API_TOKEN" : "your_api_token"
}
```

4. Create an Orchestra Pipeline with a single python taks. You should configure an input `warehouse` equal to the warehouse name. The accepted values are `snowflake`, `bigquery`, and `mysql`.
5. The command for the python task should be `python run.py ${{inputs.warehouse}}`
6. Ensure you add the `pip install -r requirements.txt` Build Command
7. If you require the data updated every [ hour ] then run the pipeline with a cron schedule, [ hourly ]. If you need it in real-time, then have the pipeline be triggered after every other pipeline completes.


