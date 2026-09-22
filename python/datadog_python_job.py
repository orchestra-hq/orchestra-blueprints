#!/usr/bin/env python3
"""Demo Python task: every log line reaches Datadog as it is written.

The other half of the demo, `datadog_logs.py`, forwards the dbt task's logs
from the Orchestra API once that task has finished. This one is the live path:
`DatadogLiveHandler` submits each record through the official Datadog API
client (`datadog-api-client`) the moment it is logged, so lines show up in
Datadog while the task is still running - and survive a task that dies partway.

Task build command: `pip install datadog-api-client`.
Connection secret: `DD_API_KEY` (or `API_KEY`); `DD_SITE` selects the region.
"""

import logging
import os

from datadog_api_client import ApiClient, Configuration
from datadog_api_client.v2.api.logs_api import LogsApi
from datadog_api_client.v2.model.http_log import HTTPLog
from datadog_api_client.v2.model.http_log_item import HTTPLogItem

from datadog_logs import api_key, tags

SOURCES = {"customers": 1_284, "orders": 9_452, "events": 0}
MIN_ROWS = 500  # a source below this is treated as a failed load


def check_row_count(rows: int) -> None:
    if rows < MIN_ROWS:
        raise ValueError(f"only {rows} rows, expected at least {MIN_ROWS}")


class DatadogLiveHandler(logging.Handler):
    """Submit each record to Datadog as it is logged - no buffering."""

    def __init__(self):
        super().__init__()
        # The SDK reads DD_API_KEY and DD_SITE from the environment.
        os.environ.setdefault("DD_API_KEY", api_key())
        self.logs = LogsApi(ApiClient(Configuration()))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.logs.submit_log(
                body=HTTPLog(
                    [
                        HTTPLogItem(
                            ddsource="python",
                            service=os.environ.get("DD_SERVICE", "orchestra"),
                            message=self.format(record),
                            status=record.levelname.lower(),
                            ddtags=tags(
                                orchestra_task_run_id=os.environ.get("ORCHESTRA_TASK_RUN_ID", ""),
                                logger=record.name,
                            ),
                        )
                    ]
                )
            )
        except Exception:  # never let log shipping kill the job
            self.handleError(record)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    # On this logger only: the SDK's own records must not feed back into it.
    log = logging.getLogger("orchestra.python_job")
    log.addHandler(DatadogLiveHandler())

    log.info("Loading %s sources", len(SOURCES))
    loaded = failed = 0
    for name, rows in SOURCES.items():
        try:
            check_row_count(rows)
        except ValueError:
            failed += 1
            log.exception("Source '%s' failed its row-count check", name)
            continue
        loaded += rows
        log.info("Loaded %s rows from source '%s'", rows, name)

    if failed:
        log.warning("%s of %s sources failed to load", failed, len(SOURCES))
    log.info("Finished - %s rows loaded", loaded)


if __name__ == "__main__":
    main()
