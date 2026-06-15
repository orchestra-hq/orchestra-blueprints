# Python workers

`python/` contains Python modules used by this repo’s demos.

Most subfolders are intended to be executed by Orchestra via Python task
integrations (i.e., Orchestra launches the Python code as part of a pipeline
run).

Platform interaction patterns live under `patterns/`.

## Contents

- Worker modules for integrations and data movement.
- Subfolders with targeted examples (for example `integration_a/`,
  `integration_b/`, and `claude_agent/`).
- Shared dependencies in `requirements.txt`.

## Live dbt Alerts

`live_dbt_alerts.py` contains a short Python script, wrapping the [Orchestra CLI](https://docs.getorchestra.io/docs/git-control-and-ci-cd/orchestra-cli), that utilises an [Orchestra Python Task](https://docs.getorchestra.io/docs/integrations/python) and dbt's logging to send real time Slack alerts for dbt runs.

### Usage

In order to run live dbt alerting for a dbt task:

* Create Slack incoming webhook(s) - Full [docs](https://docs.slack.dev/messaging/sending-messages-using-incoming-webhooks/#getting_started)
  - Create per-channel webhook to send alerts to (just 1 in this example, but can be extended)
  - Navigate (in Slack dashboard) to *Your Slack App* > *Incoming Webhooks* > Copy the Webhook URL for later

* Create Orchestra Python connection:
  - Connect to repo containing `live_dbt_alerts.py`
  - Store `SLACK_WEBHOOK` in secrets containing the Webhook URL retrieved above

* Configure pipeline tasks
  - In your dbt pipeline of choice, add `--log-level debug --log-format json` to the dbt command you are running
  - Create a Python task to run in parallel:
    - Use the connection set up above
    - Set Python command to `python live-dbt-alerts.py ${{ ORCHESTRA.PIPELINE_RUN_TASKS['<dbt task ID>'].TASK_RUN_ID }}` or wherever your alerting script is located
    - Add build command of `pip install httpx orchestra-cli git+https://github.com/orchestra-hq/orchestra-cli.git@main` or latest `orchestra-cli`

* Add alert config to dbt tests, field structure is as follows:
```yaml
- <test_name>:
    config:
      meta:
        tags:
          - "Super Urgent Data Tests"
        owner: "gary@getorchestra.io"
        channel: "#dbt-live-alerts"
        subscribers:
          - "spyro@getorchestra.io"
```

That's it! On the next run of your dbt pipeline, Orchestra will spin up a monitoring Python task to parse your dbt failures and alert you in Slack!
