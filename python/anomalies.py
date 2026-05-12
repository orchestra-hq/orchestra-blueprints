import os
import requests
from datetime import datetime, timedelta, timezone

from orchestra_sdk.orchestra import OrchestraSDK


orchestra_api_key = os.getenv("ORCHESTRA_API_KEY")
threshold = os.getenv("ANOMALY_THRESHOLD") or 2
cadence = os.getenv("ANALYSIS_CADENCE") or 15
environment = os.getenv("ENVIRONMENT") or "PROD"


### Get Pipeline IDs
def get_pipelines() -> list:
    url = "https://app.getorchestra.io/api/engine/public/pipelines"
    headers = {
        "Authorization": f"Bearer {orchestra_api_key}",
        "Content-Type": "application/json",
    }
    response = requests.request("GET", url, headers=headers)
    pipeline_ids = [x["id"] for x in response.json() if x["paused"] is False]
    print(f"There are a total of {len(pipeline_ids)} unpaused pipelines")
    return pipeline_ids


def analyse_pipeline(pipeline_id: str, threshold: int, cadence: int) -> list:
    """Filter pipelines to only include those that have had runs in the last 7 days"""

    now = datetime.now(timezone.utc)
    headers = {
        "Authorization": f"Bearer {orchestra_api_key}",
        "Content-Type": "application/json",
    }
    base_url = "https://app.getorchestra.io/api/engine/public/pipeline_runs"

    running_results = []
    current_page = 1
    while True:
        url = (
            f"{base_url}?status=RUNNING&page={current_page}&pipeline_ids={pipeline_id}"
        )
        response = requests.request("GET", url, headers=headers)
        payload = response.json()
        page_results = payload.get("results", [])
        if not page_results:
            break
        running_results.extend(page_results)
        if len(running_results) >= payload.get("total", 0):
            break
        current_page += 1

    completed_results = []
    current_page = 1
    while True:
        url = f"{base_url}?status=SUCCEEDED,FAILED&page={current_page}&pipeline_ids={pipeline_id}"
        response = requests.request("GET", url, headers=headers)
        payload = response.json()
        page_results = payload.get("results", [])
        if not page_results:
            break
        completed_results.extend(page_results)
        if len(completed_results) >= payload.get("total", 0):
            break
        current_page += 1

    total_results = len(running_results) + len(completed_results)
    if len(completed_results) == 0:
        return []
    print("The total number of pipeline runs is: " + str(total_results))
    average_time = sum(
        [
            (
                datetime.fromisoformat(x["completedAt"])
                - datetime.fromisoformat(x["createdAt"])
            ).total_seconds()
            for x in completed_results
        ]
    ) / len(completed_results)
    print(
        "The average time for the pipeline to run is: " + str(average_time) + " seconds"
    )
    output = []
    if len(running_results) > 0:
        for run in running_results:
            time_running = (
                now - datetime.fromisoformat(run["createdAt"])
            ).total_seconds()
            print(f"The pipeline has been running for {time_running} seconds")
            if time_running > average_time * threshold:
                print(
                    f"{run.get('pipelineName')} is taking significantly longer than average to run and may be experiencing an issue."
                )
                output.append(
                    {
                        "pipeline_name": run.get("pipelineName") or pipeline_id,
                        "run_id": run.get("id"),
                        "status": run.get("runStatus"),
                        "duration": time_running,
                        "average_duration": average_time,
                        "reason": "Run is taking too long",
                    }
                )

    else:
        print("No running pipelines to analyse for anomalies.")

    recently_completed = [
        run
        for run in completed_results
        if run.get("completedAt")
        and (now - datetime.fromisoformat(run["completedAt"])).total_seconds()
        <= timedelta(minutes=cadence).total_seconds()
    ]
    if len(recently_completed) > 0:
        for run in recently_completed:
            time_running = (
                datetime.fromisoformat(run["completedAt"])
                - datetime.fromisoformat(run["createdAt"])
            ).total_seconds()
            print(f"The pipeline completed in {time_running} seconds")
            if time_running < average_time * 0.5:
                print(
                    f"{run.get('pipelineName')} run at {run['createdAt']} was significantly shorter than average to run and may be experiencing an issue."
                )
                output.append(
                    {
                        "pipeline_name": run.get("pipelineName") or pipeline_id,
                        "run_id": run.get("id"),
                        "status": run.get("runStatus"),
                        "duration": time_running,
                        "average_duration": average_time,
                        "reason": "Run completed significantly faster than average",
                    }
                )

    else:
        print("No recently completed pipelines to analyse for anomalies.")

    return output


def format_pipeline_runs_as_slack_blocks(runs: list[dict]) -> list[dict]:
    """
    Formats pipeline run data into Slack Block Kit format.
    """

    status_emoji = {
        "SUCCEEDED": "✅",
        "FAILED": "❌",
        "RUNNING": "⏳",
        "CANCELLED": "⚪",
    }

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Pipeline Anomalies Summary",
            },
        },
        {"type": "divider"},
    ]

    for run in runs:
        emoji = status_emoji.get(run["status"], "❓")

        duration = round(run["duration"], 2)
        avg_duration = round(run["average_duration"], 2)

        blocks.append(
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Pipeline:*\n{run['pipeline_name']}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Status:*\n{emoji} {run['status']}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Duration:*\n{duration}s",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Average Duration:*\n{avg_duration}s",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Run ID:*\n`{run['run_id']}`",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Reason:*\n{run['reason']}",
                    },
                ],
            }
        )

        blocks.append({"type": "divider"})

    return blocks


pipelines = get_pipelines()
outputs = []
for i in pipelines:
    outputs += analyse_pipeline(i, int(threshold), int(cadence))
print(outputs)

if environment == "PROD":
    orchestra = OrchestraSDK(api_key=orchestra_api_key)
    orchestra.set_output(
        name="result", value=format_pipeline_runs_as_slack_blocks(outputs)
    )
