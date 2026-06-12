#!/usr/bin/env python3
"""Daily pipeline health sweep — classifies Orchestra pipelines and recommends actions."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

NOW = datetime(2026, 6, 12, 8, 2, 0, tzinfo=timezone.utc)
STALE_SCHEDULED_DAYS = 5
STALE_UNSCHEDULED_DAYS = 14


@dataclass
class PipelineRun:
    run_status: str
    completed_at: datetime | None
    triggered_by: list[dict]
    branch: str | None = None


@dataclass
class PipelineState:
    pipeline_id: str
    name: str
    runs: list[PipelineRun] = field(default_factory=list)
    repo_path: str | None = None
    team: str | None = None

    @property
    def latest_run(self) -> PipelineRun | None:
        return self.runs[0] if self.runs else None

    @property
    def last_success(self) -> datetime | None:
        for run in self.runs:
            if run.run_status in ("SUCCEEDED", "WARNING"):
                return run.completed_at
        return None

    @property
    def consecutive_failures(self) -> int:
        count = 0
        for run in self.runs:
            if run.run_status == "FAILED":
                count += 1
            else:
                break
        return count

    @property
    def schedule(self) -> dict | None:
        for run in self.runs:
            for trigger in run.triggered_by:
                if trigger.get("triggerType") == "SCHEDULED":
                    return trigger
        return None

    @property
    def is_scheduled(self) -> bool:
        return self.schedule is not None

    @property
    def last_run_at(self) -> datetime | None:
        return self.latest_run.completed_at if self.latest_run else None


def parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def extract_pipeline_name(text: str) -> str | None:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not line.startswith("name:"):
            continue
        rest = line[5:].strip()
        if not rest:
            return None
        if rest[0] in "'\"":
            quote = rest[0]
            if len(rest) > 1 and rest.endswith(quote):
                return rest[1:-1].strip()
            parts = [rest[1:]]
            for follow in lines[index + 1 :]:
                if follow.rstrip().endswith(quote):
                    parts.append(follow.rstrip()[:-1])
                    break
                parts.append(follow.strip())
            return " ".join(parts).strip()
        return rest.strip("'\"")
    return None


def load_repo_pipelines(root: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for pattern in ("orchestra/**/*.yml", "orchestra/**/*.yaml"):
        for path in root.glob(pattern):
            if "dbt_packages" in str(path):
                continue
            name = extract_pipeline_name(path.read_text())
            if not name:
                continue
            mapping[re.sub(r"\s+", " ", name).strip()] = str(path)
    return mapping


def normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def match_repo_path(name: str, repo: dict[str, str]) -> str | None:
    if name in repo:
        return repo[name]
    norm = normalize_name(name)
    for repo_name, path in repo.items():
        repo_norm = normalize_name(repo_name)
        if repo_norm == norm:
            return path
        if norm in repo_norm or repo_norm in norm:
            return path
        norm_tokens = set(re.findall(r"#\w+|\w+", norm))
        repo_tokens = set(re.findall(r"#\w+|\w+", repo_norm))
        if len(norm_tokens & repo_tokens) >= 3:
            return path
    return None


def extract_team(name: str) -> str | None:
    tags = re.findall(r"#(\w+)", name)
    for tag in ("teams", "slack", "dataquality", "metaengine"):
        if tag in [t.lower() for t in tags]:
            return f"#{tag}"
    return None


def classify(pipeline: PipelineState) -> str:
    if not pipeline.runs:
        return "Never run"

    latest = pipeline.latest_run
    assert latest is not None

    if latest.run_status == "FAILED" or pipeline.consecutive_failures >= 3:
        return "Failing"

    last_success = pipeline.last_success
    last_run = pipeline.last_run_at

    if pipeline.is_scheduled:
        if last_success is None or (NOW - last_success) > timedelta(days=STALE_SCHEDULED_DAYS):
            return "Stale"
    elif last_run is None or (NOW - last_run) > timedelta(days=STALE_UNSCHEDULED_DAYS):
        return "Stale"

    if not extract_team(pipeline.name) and not pipeline.is_scheduled:
        if last_run and (NOW - last_run) > timedelta(days=STALE_UNSCHEDULED_DAYS):
            return "Orphaned"

    if latest.run_status in ("SUCCEEDED", "WARNING"):
        return "Healthy"

    return "Healthy"


def ingest_runs(data: dict) -> dict[str, PipelineState]:
    pipelines: dict[str, PipelineState] = {}
    for row in data.get("results", []):
        pid = row["pipelineId"]
        if pid not in pipelines:
            pipelines[pid] = PipelineState(
                pipeline_id=pid,
                name=row["pipelineName"],
            )
        pipelines[pid].runs.append(
            PipelineRun(
                run_status=row["runStatus"],
                completed_at=parse_ts(row.get("completedAt") or row.get("updatedAt")),
                triggered_by=row.get("triggeredBy") or [],
                branch=row.get("branch"),
            )
        )
    for state in pipelines.values():
        state.runs.sort(
            key=lambda r: r.completed_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
    return pipelines


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    runs_path = Path(sys.argv[1]) if len(sys.argv) > 1 else root / ".sweep_cache" / "runs.json"
    runs_data = json.loads(runs_path.read_text())
    repo = load_repo_pipelines(root)

    pipelines = ingest_runs(runs_data)
    for state in pipelines.values():
        state.repo_path = match_repo_path(state.name, repo)
        state.team = extract_team(state.name)

    # Repo-only pipelines not seen in workspace runs
    matched_paths = {p.repo_path for p in pipelines.values() if p.repo_path}
    repo_only = [
        (name, path)
        for name, path in repo.items()
        if path not in matched_paths
    ]

    results: list[dict] = []
    for pid, state in sorted(pipelines.items(), key=lambda x: x[1].name):
        classification = classify(state)
        latest = state.latest_run
        results.append(
            {
                "pipeline_id": pid,
                "name": state.name,
                "classification": classification,
                "last_run_status": latest.run_status if latest else "never",
                "last_run_at": latest.completed_at.isoformat() if latest and latest.completed_at else None,
                "last_success_at": state.last_success.isoformat() if state.last_success else None,
                "consecutive_failures": state.consecutive_failures,
                "scheduled": state.is_scheduled,
                "schedule_cron": (state.schedule or {}).get("scheduleCron"),
                "repo_path": state.repo_path,
                "team": state.team,
            }
        )
        print(
            f"AUDIT: {classification:10} | {pid[:8]} | {state.name[:55]:55} | "
            f"last={latest.run_status if latest else 'none':10} | repo={'yes' if state.repo_path else 'no'}"
        )

    print(f"\nAUDIT: Repo configs without workspace runs: {len(repo_only)}")
    for name, path in sorted(repo_only, key=lambda x: x[1]):
        print(f"AUDIT: REPO_ONLY | {path} | {name[:60]}")

    out = {
        "sweep_date": NOW.date().isoformat(),
        "pipelines": results,
        "repo_only": [{"name": n, "path": p} for n, p in repo_only],
        "healthy_count": sum(1 for r in results if r["classification"] == "Healthy"),
        "non_healthy": [r for r in results if r["classification"] != "Healthy"],
    }
    out_path = root / ".sweep_cache" / "classification.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nWrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
