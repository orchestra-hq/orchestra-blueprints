"""Dummy Python script used to smoke-test the Orchestra register -> run -> promote flow.

Deliberately dependency-free (standard library only) so the Orchestra PYTHON task
needs no build_command and the run stays fast and cheap. It does just enough to be
a meaningful smoke test:

  * proves the repo was cloned and the working directory is correct
  * proves environment variables reach the task
  * emits a few log lines so the task run has something to show
  * exits non-zero on an explicit failure switch, so the promote gate can be tested
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timezone

# Set FAIL_ON_PURPOSE=true on the task to force a failure. Useful for checking
# that the "promote to the other workspace" job really is gated on success.
FAIL_ON_PURPOSE = os.environ.get("FAIL_ON_PURPOSE", "false").lower() == "true"
ROW_COUNT = int(os.environ.get("ROW_COUNT", "5"))


def log(message: str) -> None:
    """Print with a UTC timestamp and flush, so logs stream in the Orchestra UI."""
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{stamp}] {message}", flush=True)


def main() -> int:
    log("Dummy pipeline task starting")
    log(f"python={sys.version.split()[0]} cwd={os.getcwd()}")
    log(f"ORCHESTRA_ENVIRONMENT={os.environ.get('ORCHESTRA_ENVIRONMENT', '<unset>')}")

    # Stand-in for real work: pretend to process a handful of rows.
    for row in range(1, ROW_COUNT + 1):
        time.sleep(0.2)
        log(f"processed row {row}/{ROW_COUNT}")

    if FAIL_ON_PURPOSE:
        log("FAIL_ON_PURPOSE is set - failing deliberately")
        return 1

    log(f"Dummy pipeline task finished OK ({ROW_COUNT} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
