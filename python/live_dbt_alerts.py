#!/usr/bin/env python3
"""Stream dbt task logs from Orchestra and send Slack alerts on test failures."""

import json
import os
import subprocess
import sys
import time

import httpx

BASE_URL = "https://app.getorchestra.io/api/engine/public"
ORCHESTRA_API_KEY = os.environ.get("ORCHESTRA_API_KEY", "")
SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK", "")

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 3
HTTP_TIMEOUT_SECONDS = 10


def timestamp() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def send_slack_message(payload: dict) -> None:
    if not SLACK_WEBHOOK:
        print("SLACK_WEBHOOK not set; skipping alert")
        return
    try:
        httpx.post(SLACK_WEBHOOK, json=payload, timeout=HTTP_TIMEOUT_SECONDS)
    except httpx.HTTPError as exc:
        print(f"Failed to send Slack message: {exc}")


def fetch_task_run(task_run_id: str) -> dict:
    """Fetch task run details from Orchestra, retrying with exponential backoff."""
    for attempt in range(MAX_RETRIES):
        try:
            response = httpx.get(
                f"{BASE_URL}/task_runs",
                headers={"Authorization": f"Bearer {ORCHESTRA_API_KEY}"},
                params={"task_run_ids": task_run_id},
                timeout=HTTP_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError:
            if attempt == MAX_RETRIES - 1:
                raise
            time.sleep(1)
    raise RuntimeError("unreachable")


def wait_for_log_stream(task_run_id: str, dbt_command: str) -> subprocess.Popen:
    """Spawn orchestra-cli repeatedly until the log stream is available."""
    while True:
        process = subprocess.Popen(
            [
                "orchestra-cli", "task", "logs",
                "--task-run-id", task_run_id,
                "--filename", f"1/{dbt_command}",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=os.environ.copy(),
        )

        time.sleep(1)

        # Process died immediately -> logs not ready yet.
        if process.poll() is None:
            line = process.stdout.readline()
            if line and "Download task log failed" not in line:
                print(line, end="")
                return process
            process.terminate()

        time.sleep(RETRY_DELAY_SECONDS)


def parse_test_identifiers(data: dict) -> tuple[str, str, str]:
    """Split a dbt test node name into (model, test_name, column)."""
    model = data.get("attached_node", "").split(".")[-1]
    base = data.get("name", "").rsplit("__", 1)[0]
    test_name, _, remainder = base.partition(f"_{model}")
    # A "__" prefix is meaningful: strip only one underscore to keep the rest.
    column = remainder[1:] if remainder.startswith("__") else remainder.lstrip("_")
    return model, test_name, column


def build_alert_message(data: dict) -> dict:
    """Build a Slack Block Kit payload styled as a test-failure card."""
    model, test_name, column = parse_test_identifiers(data)
    meta = data.get("node_info", {}).get("meta", {})
    owner = meta.get("owner", "Unknown")
    subscribers = meta.get("subscribers", [])
    tags = meta.get("tags", [])
    failures = data.get("num_failures", "unknown")
    status = data.get("status", "fail").upper()
    failed_at = data.get("node_info", {}).get("node_finished_at", "")
    alerted_at = timestamp()

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "\U0001F6A8 dbt Test Failure", "emoji": True},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Model*\n`{model}`"},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Owner*\n{owner}"},
                {"type": "mrkdwn", "text": f"*Channel*\n`{meta.get('channel', '')}`"},
                {"type": "mrkdwn", "text": f"*Column*\n{column}"},
                {"type": "mrkdwn", "text": f"*Test name*\n{test_name}"},
                {"type": "mrkdwn", "text": f"*Subscribers*\n{', '.join(subscribers) if subscribers else 'None'}"},
                {"type": "mrkdwn", "text": f"*Tags*\n{', '.join(tags) if tags else 'None'}"},
            ],
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"\U0001F50E *Result*\n```Got {failures} failures, status: {status}```",
            },
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"Failed at {failed_at}  \u2022  Alerted at {alerted_at}"},
            ],
        },
    ]

    # Fallback text for notifications and clients that don't render blocks.
    fallback = f"dbt test failure: {test_name} on {model}.{column} ({failures} failures)"

    # Blocks live inside the attachment so the red sidebar spans the whole card.
    return {
        "text": fallback,
        "attachments": [{"color": "#E01E5A", "blocks": blocks}],
    }


def is_test_failure(log: dict) -> bool:
    info = log.get("info", {})
    data = log.get("data", {})
    channel = data.get("node_info", {}).get("meta", {}).get("channel", "")
    return (
        info.get("name") == "LogTestResult"
        and data.get("status", "").lower() in ("fail", "warn")
        and channel != ""
    )


def watch_logs(process: subprocess.Popen) -> None:
    """Stream log lines, alerting on test failures, until run stats appear."""
    print("Looping:", timestamp())

    for line in process.stdout:
        print("Line:", timestamp(), line)
        try:
            log = json.loads(line)
        except json.JSONDecodeError:
            continue

        data = log.get("data", {})

        if "stats" in data:
            print("breaking", data)
            return

        if is_test_failure(log):
            print("Data:", data)
            send_slack_message(build_alert_message(data))

    print("Process exited without 'stats' in data")


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(f"Usage: {sys.argv[0]} <task_run_id>")

    task_run_id = sys.argv[1]
    print("Logging for Task Run ID:", task_run_id)
    print("Starting:", timestamp())

    task_run = fetch_task_run(task_run_id)
    result = task_run.get("results", [{}])[0]
    dbt_command = result.get("taskParameters", {}).get("commands")
    print("dbt Task Status:", result.get("status", ""))

    process = wait_for_log_stream(task_run_id, dbt_command)
    try:
        watch_logs(process)
    finally:
        process.wait()


if __name__ == "__main__":
    main()
