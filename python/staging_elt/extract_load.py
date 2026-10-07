"""Simulated extract-and-load worker for the staging end-to-end blueprint.

This is the ``EL`` step of ``orchestra/staging_end_to_end_elt.yml``. It stands in
for a real source-system extract: it generates a deterministic batch of records
for one source, writes them to a newline-delimited JSON landing file, and reports
the batch back to Orchestra as task outputs so downstream ``T`` and downstream
tasks can reference them.

Everything here is standard library plus ``orchestra-sdk`` (pre-installed in the
Orchestra Python task runtime), so the task needs no build step and stays fast.

Environment variables
---------------------
SOURCE_NAME      Logical source being extracted (set per matrix iteration).
TARGET_TABLE     Table the batch is destined for in the warehouse.
ENV_NAME         Deployment environment, e.g. ``staging``. Default ``staging``.
BATCH_SIZE       Number of rows to simulate. Default ``250``.
LANDING_DIR      Directory for the landing files. Default ``./landing``.
ORCHESTRA_API_KEY / ORCHESTRA_TASK_RUN_ID  Injected by Orchestra at runtime.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SOURCE_NAME = os.getenv("SOURCE_NAME", "unknown_source")
TARGET_TABLE = os.getenv("TARGET_TABLE", SOURCE_NAME)
ENV_NAME = os.getenv("ENV_NAME", "staging")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "250"))
LANDING_DIR = Path(os.getenv("LANDING_DIR", "./landing"))

PIPELINE_RUN_ID = os.getenv("ORCHESTRA_PIPELINE_RUN_ID", "local")
TASK_RUN_ID = os.getenv("ORCHESTRA_TASK_RUN_ID", "local")


def batch_id() -> str:
    """Deterministic id for this (run, source) pair, so re-runs are traceable."""
    digest = hashlib.sha256(f"{PIPELINE_RUN_ID}:{SOURCE_NAME}".encode()).hexdigest()
    return f"{ENV_NAME}-{SOURCE_NAME}-{digest[:12]}"


def extract(rows: int) -> list[dict]:
    """Simulate paging a source API and returning raw records."""
    rng = random.Random(batch_id())
    now = datetime.now(timezone.utc)
    records = []
    for i in range(rows):
        records.append(
            {
                "record_id": f"{SOURCE_NAME}-{i:06d}",
                "source": SOURCE_NAME,
                "extracted_at": (now - timedelta(seconds=rng.randint(0, 86_400))).isoformat(),
                "amount": round(rng.uniform(1.0, 5_000.0), 2),
                "region": rng.choice(["EMEA", "AMER", "APAC"]),
                "is_active": rng.random() > 0.1,
                "_batch_id": batch_id(),
                "_pipeline_run_id": PIPELINE_RUN_ID,
            }
        )
    return records


def load(records: list[dict]) -> Path:
    """Write the batch to the landing zone as newline-delimited JSON."""
    LANDING_DIR.mkdir(parents=True, exist_ok=True)
    landing_file = LANDING_DIR / f"{TARGET_TABLE}__{batch_id()}.jsonl"
    with landing_file.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")
    return landing_file


def publish_outputs(summary: dict) -> None:
    """Hand the batch summary back to Orchestra for downstream tasks."""
    api_key = os.getenv("ORCHESTRA_API_KEY")
    if not api_key:
        print("ORCHESTRA_API_KEY not set - skipping output publication.")
        return
    try:
        from orchestra_sdk.orchestra import OrchestraSDK
    except ImportError:
        print("orchestra-sdk not available - skipping output publication.")
        return

    orchestra = OrchestraSDK(api_key=api_key)
    orchestra.set_output(name="rows_loaded", value=str(summary["rows_loaded"]))
    orchestra.set_output(name="batch_id", value=summary["batch_id"])
    orchestra.set_output(name="target_table", value=summary["target_table"])
    orchestra.set_output(name="load_summary", value=json.dumps(summary))


def main() -> int:
    if BATCH_SIZE <= 0:
        print(f"BATCH_SIZE must be positive, got {BATCH_SIZE}", file=sys.stderr)
        return 1

    print(f"[{ENV_NAME}] Extracting {BATCH_SIZE} records from '{SOURCE_NAME}'...")
    records = extract(BATCH_SIZE)

    landing_file = load(records)
    print(f"[{ENV_NAME}] Loaded {len(records)} records to {landing_file}")

    summary = {
        "environment": ENV_NAME,
        "source": SOURCE_NAME,
        "target_table": TARGET_TABLE,
        "batch_id": batch_id(),
        "rows_loaded": len(records),
        "landing_file": str(landing_file),
        "pipeline_run_id": PIPELINE_RUN_ID,
        "task_run_id": TASK_RUN_ID,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    print(json.dumps(summary, indent=2))

    publish_outputs(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
