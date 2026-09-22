#!/usr/bin/env python3
"""Demo Python task: logs go to Datadog as the work happens.

The other half of the demo, `datadog_logs.py`, forwards the dbt task's logs
after that task has finished. This one shows the live path - every line this
task logs is shipped by `DatadogHandler` with `ddsource:python`, including
warnings and tracebacks.

The "work" below is stand-in data; the point is the log levels that come out of
it. Uses the same Python connection, so `DD_API_KEY` (or `API_KEY`) applies.
"""

import logging

from datadog_logs import setup_logging

SOURCES = {"customers": 1_284, "orders": 9_452, "events": 0}


def main() -> None:
    log = setup_logging("orchestra.python_job")
    log.info("Loading %s sources", len(SOURCES))

    loaded = 0
    for name, rows in SOURCES.items():
        if not rows:
            log.warning("Source '%s' returned no rows - downstream models may be stale", name)
            continue
        loaded += rows
        log.info("Loaded %s rows from source '%s'", rows, name)

    try:
        log.info("Events per load: %.2f", loaded / SOURCES["events"])
    except ZeroDivisionError:
        log.exception("Could not compute events per load")

    log.info("Finished - %s rows loaded", loaded)
    logging.shutdown()


if __name__ == "__main__":
    main()
