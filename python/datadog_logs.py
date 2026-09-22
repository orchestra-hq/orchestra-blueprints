#!/usr/bin/env python3
"""Send Orchestra Python and dbt Core logs to Datadog.

Run this as a Python task downstream of the tasks you want in Datadog:

* its own ``logging`` output is shipped live by :class:`DatadogHandler`
* every other task run in the same pipeline run (dbt Core included) has its
  log files pulled from the Orchestra API and forwarded line by line

Stdlib only, so the task needs no build command.

Connection secret required: ``DD_API_KEY``.
Optional env vars: ``DD_SITE`` (default ``datadoghq.eu``), ``DD_SERVICE``, ``DD_ENV``.
``ORCHESTRA_API_KEY``, ``ORCHESTRA_PIPELINE_RUN_ID`` and ``ORCHESTRA_TASK_RUN_ID``
are injected by Orchestra.
"""

import json
import logging
import logging.handlers
import os
import re
import urllib.error
import urllib.parse
import urllib.request

ORCHESTRA_API = "https://app.getorchestra.io/api/engine/public"
BATCH_SIZE = 500  # Datadog caps one intake array at 1000 entries / 5MB
MAX_MESSAGE = 100_000  # Datadog drops anything over 1MB per log
TIMEOUT = 30

ANSI = re.compile(r"\x1b\[[0-9;]*m")
log = logging.getLogger("orchestra.datadog")


def site() -> str:
    return os.environ.get("DD_SITE", "datadoghq.eu")


def tags(**extra: str) -> str:
    """Datadog `ddtags` string, dropping empty values."""
    pairs = {
        "env": os.environ.get("DD_ENV", "prod"),
        "orchestra_pipeline_run_id": os.environ.get("ORCHESTRA_PIPELINE_RUN_ID", ""),
        **extra,
    }
    return ",".join(f"{k}:{v}" for k, v in pairs.items() if v)


def strip_ansi(line: str) -> str:
    return ANSI.sub("", line).rstrip()


def status_of(line: str) -> str:
    """Best-effort Datadog status from a plain-text log line."""
    upper = line.upper()
    if "ERROR" in upper or "FAIL" in upper or "TRACEBACK" in upper:
        return "error"
    if "WARN" in upper:
        return "warn"
    return "info"


def chunks(items: list, size: int = BATCH_SIZE):
    for start in range(0, len(items), size):
        yield items[start : start + size]


def send(events: list) -> None:
    """POST log events to the Datadog HTTP intake, in batches."""
    api_key = os.environ.get("DD_API_KEY", "")
    if not api_key:
        print("DD_API_KEY not set; skipping Datadog send")
        return
    url = f"https://http-intake.logs.{site()}/api/v2/logs"
    for batch in chunks(events):
        request = urllib.request.Request(
            url,
            data=json.dumps(batch).encode(),
            headers={"DD-API-KEY": api_key, "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                response.read()
        except urllib.error.HTTPError as exc:
            # Never fail the pipeline because log shipping failed.
            print(f"Datadog intake returned {exc.code}: {exc.read()[:500]!r}")
        except urllib.error.URLError as exc:
            print(f"Datadog intake unreachable: {exc}")


class DatadogHandler(logging.handlers.BufferingHandler):
    """Buffer Python log records and flush them to Datadog.

    `logging.shutdown()` closes handlers at interpreter exit, which flushes
    whatever is left in the buffer.
    """

    def __init__(self, capacity: int = BATCH_SIZE):
        super().__init__(capacity)

    def flush(self) -> None:
        self.acquire()
        try:
            if not self.buffer:
                return
            send(
                [
                    {
                        "ddsource": "python",
                        "service": os.environ.get("DD_SERVICE", "orchestra"),
                        "status": record.levelname.lower(),
                        "message": self.format(record),
                        "ddtags": tags(
                            orchestra_task_run_id=os.environ.get("ORCHESTRA_TASK_RUN_ID", ""),
                            logger=record.name,
                        ),
                    }
                    for record in self.buffer
                ]
            )
            self.buffer = []
        finally:
            self.release()


def orchestra_get(path: str, **params: str):
    """GET an Orchestra API path, returning parsed JSON (or raw bytes for logs)."""
    url = f"{ORCHESTRA_API}{path}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {os.environ.get('ORCHESTRA_API_KEY', '')}"}
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        body = response.read()
    return body if path.endswith("/download") else json.loads(body)


def task_runs(pipeline_run_id: str) -> list:
    """Every task run in the pipeline run, latest attempt only."""
    results, page = [], 1
    while True:
        payload = orchestra_get(
            f"/pipeline_runs/{pipeline_run_id}/task_runs",
            page=str(page),
            page_size="50",
            include_superseded="false",
        )
        results += payload.get("results", [])
        if len(results) >= payload.get("total", 0) or not payload.get("results"):
            return results
        page += 1


def ship_task_run(pipeline_run_id: str, task_run: dict) -> int:
    """Forward one task run's log files to Datadog. Returns lines shipped."""
    task_run_id = task_run["id"]
    listing = orchestra_get(f"/pipeline_runs/{pipeline_run_id}/task_runs/{task_run_id}/logs")
    integration = (task_run.get("integration") or "unknown").lower()
    source = "dbt" if integration.startswith("dbt") else integration
    events = []
    for filename in listing.get("filenames", []):
        if filename.rsplit("/", 1)[-1] == "debug_task":
            continue  # Orchestra's own container debug log, not the job's output
        raw = orchestra_get(
            f"/pipeline_runs/{pipeline_run_id}/task_runs/{task_run_id}/logs/download",
            filename=filename,
        )
        for line in raw.decode("utf-8", "replace").splitlines():
            line = strip_ansi(line)
            if not line:
                continue
            events.append(
                {
                    "ddsource": source,
                    "service": os.environ.get("DD_SERVICE", "orchestra"),
                    "status": status_of(line),
                    "message": line[:MAX_MESSAGE],
                    "ddtags": tags(
                        orchestra_task_run_id=task_run_id,
                        task_name=task_run.get("taskName", ""),
                        integration=integration,
                        task_status=(task_run.get("status") or "").lower(),
                        log_file=filename,
                    ),
                }
            )
    send(events)
    return len(events)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger().addHandler(DatadogHandler())

    pipeline_run_id = os.environ.get("ORCHESTRA_PIPELINE_RUN_ID", "")
    self_task_run_id = os.environ.get("ORCHESTRA_TASK_RUN_ID", "")
    if not os.environ.get("DD_API_KEY"):
        log.error("DD_API_KEY is missing - add it to the Python connection's Secret JSON")
    log.info("Shipping logs for pipeline run %s to Datadog (%s)", pipeline_run_id, site())

    shipped = 0
    for task_run in task_runs(pipeline_run_id):
        if task_run["id"] == self_task_run_id or task_run.get("matrixParent"):
            continue
        lines = ship_task_run(pipeline_run_id, task_run)
        shipped += lines
        log.info("Shipped %s log lines from task '%s'", lines, task_run.get("taskName"))

    log.info("Done - %s log lines sent to Datadog", shipped)
    logging.shutdown()


if __name__ == "__main__":
    main()
