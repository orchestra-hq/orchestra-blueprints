#!/usr/bin/env python3
"""Classify Orchestra pipelines from list_pipelines JSON. Writes audit log to stdout."""

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

STALE_SCHED = timedelta(days=5)
STALE_UNSCHED = timedelta(days=14)
OK = {"SUCCEEDED", "WARNING", "RUNNING"}


def ts(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def jload(value) -> list:
    if not value or value == "[]":
        return []
    return json.loads(value) if isinstance(value, str) else value


def webhook_enabled(pipeline: dict) -> bool:
    webhook = pipeline.get("webhook")
    if not webhook:
        return False
    if isinstance(webhook, dict):
        return bool(webhook.get("enabled"))
    try:
        return bool(json.loads(webhook).get("enabled"))
    except json.JSONDecodeError:
        return False


def has_active_trigger(pipeline: dict) -> bool:
    return (
        bool(jload(pipeline.get("schedule")))
        or bool(jload(pipeline.get("sensors")))
        or bool(jload(pipeline.get("trigger_events")))
        or webhook_enabled(pipeline)
    )


def repo_file_exists(pipeline: dict) -> bool | None:
    if pipeline.get("repository") != "orchestra-hq/orchestra-blueprints":
        return None
    yaml_path = pipeline.get("yaml_path")
    return bool(yaml_path and Path(yaml_path).exists())


def classify(pipeline: dict, now: datetime) -> tuple[str, str]:
    last = ts(pipeline.get("latest_run_completed_at") or pipeline.get("latest_run_created_at"))
    scheduled = bool(jload(pipeline.get("schedule")))
    status = pipeline.get("latest_run_status")
    never = not pipeline.get("latest_run_id")

    if never:
        orphaned = not pipeline.get("product_name") and not has_active_trigger(pipeline)
        state = "orphaned+never-run" if orphaned else "never-run"
        return state, "zero run history"

    if status == "FAILED":
        return "failing", f"last run FAILED ({last.date() if last else '?'})"

    if status == "CANCELLED" and scheduled:
        return "failing", "scheduled run cancelled"

    if scheduled and last and status in OK:
        if (now - last) <= STALE_SCHED:
            return "healthy", "within schedule window"
        if status in {"SUCCEEDED", "WARNING"}:
            return "stale", f"scheduled, last ok run {(now - last).days}d ago"

    if not scheduled and last and status in OK:
        if (now - last) <= STALE_UNSCHED:
            return "healthy", "manual/sensor, recent run"
        if status in {"SUCCEEDED", "WARNING"}:
            if not pipeline.get("product_name") and not has_active_trigger(pipeline):
                return "stale+orphaned", f"no team/schedule, last ok {(now - last).days}d ago"
            return "stale", f"no schedule, last ok {(now - last).days}d ago"

    if status in OK:
        return "healthy", status.lower()

    return "unknown", str(status)


def suggested_action(state: str, pipeline: dict) -> str:
    if state == "failing" and pipeline.get("yaml_path") == "orchestra/snowflake_quality_tests.yml":
        return "PR: restore yaml"
    if "never-run" in state and pipeline.get("storage_provider") == "GITHUB" and not has_active_trigger(pipeline):
        return "PR: remove config"
    if state == "failing":
        return "Slack: manual attention"
    if state == "stale":
        return "ignore (last run ok)"
    return "skip"


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: classify.py <pipelines.json>", file=sys.stderr)
        return 1

    pipelines = json.loads(Path(sys.argv[1]).read_text())
    now = datetime.now(timezone.utc)
    buckets: dict[str, list] = {}

    for pipeline in pipelines:
        state, reason = classify(pipeline, now)
        buckets.setdefault(state, []).append(pipeline)
        action = suggested_action(state, pipeline)
        print(
            f"AUDIT | {pipeline['id'][:8]} | {pipeline['name'][:40]:40} | "
            f"{state:18} | {reason:30} | {action}"
        )

    print("\n=== SUMMARY ===")
    for key in sorted(buckets):
        print(f"{key}: {len(buckets[key])}")
    print(f"total: {len(pipelines)}")
    print(f"healthy_skipped: {len(buckets.get('healthy', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
