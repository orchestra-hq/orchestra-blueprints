---
name: create-dq-rules
description: Reads Snowflake Metadata to construct a pipeline with DQ Rules
---

1. Use the Snowflake credentials which are formatted dlt-style in environment variables to connect to snowflake and get the lists of databases, schema and tables
2. Query a subset of data for 3 tables
3. based on these, think of some SQL Queries you can run as dbt-style data quality rules, checking for things like nulls, irregular values, duplicates and so on
4. Use these to construct an Orchestra pipeline as specified below. Use the Orchestra-CLI to validate the pipeline. You should only be changing the SQL Statement field in the SNOWFLAKE_RUN_TEST Task and the matrix vlaues i.e. to parameterise the test


Example pipeline:
```yml
version: v1
name: 'Snowflake Data Quality Tests #snowflake #dataquality'
pipeline:
  3e058349-56be-4175-b835-e877e5ce12db:
    tasks:
      cf917cfd-7a64-4e88-83b0-5217409d92a8:
        integration: SNOWFLAKE
        integration_job: SNOWFLAKE_RUN_TEST
        parameters:
          statement: 'select * from BIGQUERY_SAMPLE.PUBLIC.${{ MATRIX.dq_inputs[''table'']
            }}

            where ${{ MATRIX.dq_inputs[''column''] }} is null

            limit 100'
          error_threshold_expression: '> 0'
          warn_threshold_expression: '> 0'
        depends_on: []
        name: Not Null test
        connection: ${{ ENV.SNOWFLAKE_CONNECTION }}
    depends_on:
    - 5c6e2fd1-7782-4a79-9850-0daf332a6f79
    name: ''
    matrix:
      inputs:
        dq_inputs:
        - table: issues
          column: _airbyte_raw_id
        - table: USERS
          column: COUNTRY
schedule:
- name: Daily at 8am
  cron: 0 8 ? * FRI *
  timezone: Europe/London
webhook:
  enabled: false
inputs:
  tablename:
    type: string
    default: hubspot_contacts_raw
alerts:
- name: Failures
  statuses:
  - FAILED
  destinations:
  - integration: SLACK
    destination: alert-testing
- name: Slack
  statuses:
  - FAILED
  destinations:
  - integration: SLACK
    destination: alert-testing

```