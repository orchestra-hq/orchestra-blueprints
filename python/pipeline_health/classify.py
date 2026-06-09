"""Classify Orchestra pipelines from aggregated run JSON files."""

import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

NON_FAILING_STATUSES = frozenset({"SUCCEEDED", "WARNING"})


def load_repo_pipelines(workspace: Path):
    mapping = {}
    for pattern in ("orchestra/**/*.yml", "orchestra/**/*.yaml", "metadata_api/**/*.yaml"):
        for p in workspace.glob(pattern):
            text = p.read_text()
            m = re.search(r"^name:\s*(.+)$", text, re.M)
            if not m:
                continue
            name = m.group(1).strip().strip("'\"").replace("\n", " ").strip()
            mapping[name] = str(p.relative_to(workspace))
            sched = re.search(r"^schedule:", text, re.M)
            mapping[f"_sched_{name}"] = bool(sched)
    return mapping


def match_repo(name, repo):
    if name in repo:
        return repo[name]
    base = name.split("#")[0].strip()
    for n, path in repo.items():
        if n.startswith("_"):
            continue
        if n.split("#")[0].strip() == base:
            return path
    return None


def parse_ts(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_runs(paths):
    runs = []
    for path in paths:
        data = json.loads(Path(path).read_text())
        runs.extend(data.get("results", []))
    return runs


def aggregate(runs):
    by_id = defaultdict(list)
    for run in runs:
        by_id[run["pipelineId"]].append(run)
    for pid in by_id:
        by_id[pid].sort(key=lambda x: x["createdAt"], reverse=True)
    return by_id


def trigger_types(run):
    return {t.get("triggerType") for t in run.get("triggeredBy", [])}


def is_scheduled_run(run):
    return "SCHEDULED" in trigger_types(run)


def is_manual_run(run):
    return "MANUAL" in trigger_types(run)


def get_schedule_info(run):
    for trigger in run.get("triggeredBy", []):
        if trigger.get("triggerType") == "SCHEDULED":
            return {
                "cron": trigger.get("scheduleCron"),
                "name": trigger.get("scheduleName"),
                "timezone": trigger.get("scheduleTimezone"),
            }
    return None


def schedule_removed_with_healthy_manual(runs, now):
    """True when the schedule no longer fires and recent manual runs are not failing."""
    latest = runs[0]
    if latest["runStatus"] not in NON_FAILING_STATUSES:
        return False
    if not is_manual_run(latest):
        return False

    scheduled_runs = [r for r in runs if is_scheduled_run(r)]
    if not scheduled_runs:
        return True

    last_scheduled = scheduled_runs[0]
    last_scheduled_at = parse_ts(
        last_scheduled["completedAt"] or last_scheduled["createdAt"]
    )
    latest_at = parse_ts(latest["completedAt"] or latest["createdAt"])
    if latest_at <= last_scheduled_at:
        return False

    latest_day = latest_at.date()
    for run in runs:
        if not is_scheduled_run(run):
            continue
        run_at = parse_ts(run["completedAt"] or run["createdAt"])
        if run_at.date() == latest_day:
            return False
        if last_scheduled_at < run_at <= latest_at:
            return False

    return True


def schedule_still_active(runs, now, repo, name):
    if is_scheduled_run(runs[0]):
        return True

    scheduled_runs = [r for r in runs if is_scheduled_run(r)]
    if not scheduled_runs:
        return bool(repo.get(f"_sched_{name}"))

    recent_days = {now.date(), (now - timedelta(days=1)).date()}
    for run in scheduled_runs:
        run_day = parse_ts(run["completedAt"] or run["createdAt"]).date()
        if run_day in recent_days:
            return True
    return False


def classify_pipeline(pid, runs, repo, now):
    name = runs[0]["pipelineName"]
    env = runs[0].get("envName", "Production")
    latest = runs[0]
    latest_status = latest["runStatus"]
    latest_at = parse_ts(latest["completedAt"] or latest["createdAt"])

    last_success = None
    consecutive_failures = 0
    for run in runs:
        if run["runStatus"] == "SUCCEEDED":
            last_success = parse_ts(run["completedAt"] or run["createdAt"])
            break
        if run["runStatus"] == "FAILED":
            consecutive_failures += 1
        else:
            break

    scheduled_runs = [r for r in runs if is_scheduled_run(r)]
    last_scheduled = scheduled_runs[0] if scheduled_runs else None
    schedule = get_schedule_info(last_scheduled) if last_scheduled else None
    is_scheduled = schedule_still_active(runs, now, repo, name)

    repo_path = match_repo(name, repo)
    in_repo = repo_path is not None

    if not runs:
        state = "Never run"
    elif latest_status == "FAILED" or consecutive_failures >= 3:
        state = "Failing"
    elif latest_status == "WARNING":
        state = "Degraded"
    elif is_scheduled and (last_success is None or (now - last_success) > timedelta(days=5)):
        state = "Stale"
    elif not is_scheduled and (now - latest_at) > timedelta(days=14):
        state = "Stale"
    elif not is_scheduled and last_success is None:
        state = "Orphaned"
    elif latest_status == "SUCCEEDED" and is_scheduled:
        if last_success and (now - last_success) <= timedelta(days=2):
            state = "Healthy"
        elif last_success and (now - last_success) <= timedelta(days=5):
            state = "Healthy"
        else:
            state = "Stale"
    elif latest_status == "SUCCEEDED":
        state = "Healthy"
    else:
        state = "Degraded"

    if state == "Degraded" and schedule_removed_with_healthy_manual(runs, now):
        state = "Healthy"

    return {
        "pipeline_id": pid,
        "name": name,
        "env": env,
        "state": state,
        "latest_status": latest_status,
        "latest_at": latest_at.isoformat(),
        "last_success": last_success.isoformat() if last_success else None,
        "consecutive_failures": consecutive_failures,
        "is_scheduled": is_scheduled,
        "schedule": schedule,
        "in_repo": in_repo,
        "repo_path": repo_path,
        "run_count": len(runs),
    }


def main():
    run_files = sys.argv[1:]
    workspace = Path(__file__).resolve().parents[2]
    now = datetime.now(timezone.utc)
    repo = load_repo_pipelines(workspace)
    runs = load_runs(run_files)
    by_id = aggregate(runs)

    results = []
    for pid, pipeline_runs in sorted(by_id.items(), key=lambda x: x[1][0]["pipelineName"]):
        results.append(classify_pipeline(pid, pipeline_runs, repo, now))

    seen_names = {r["name"] for r in results}
    repo_only = []
    for name, path in sorted(repo.items()):
        if name.startswith("_"):
            continue
        if not any(name.split("#")[0].strip() == n.split("#")[0].strip() for n in seen_names):
            repo_only.append({"name": name, "repo_path": path})

    out = {
        "pipelines": results,
        "repo_only": repo_only,
        "sweep_date": now.date().isoformat(),
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
