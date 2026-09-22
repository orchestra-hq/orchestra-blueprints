#!/usr/bin/env python3
"""Self-check for datadog_logs.py: `python test_datadog_logs.py`."""

import datadog_logs as dd


def test_strip_ansi():
    assert dd.strip_ansi("07:02:07  [dbt] Done.\x1b[0m\n") == "07:02:07  [dbt] Done."
    assert dd.strip_ansi("   ") == ""


def test_status_of():
    assert dd.status_of("12:00:01 Completed with 1 error") == "error"
    assert dd.status_of("12:00:01 1 of 2 WARN got 3 results") == "warn"
    assert dd.status_of("12:00:01 OK created sql table model dim_customers") == "info"


def test_api_key_falls_back_to_API_KEY():
    import os

    os.environ.pop("DD_API_KEY", None)
    os.environ["API_KEY"] = "from-connection"
    assert dd.api_key() == "from-connection"
    os.environ["DD_API_KEY"] = "explicit"
    assert dd.api_key() == "explicit"


def test_chunks():
    assert list(dd.chunks([1, 2, 3], 2)) == [[1, 2], [3]]
    assert list(dd.chunks([], 2)) == []


def test_tags_drops_empties():
    import os

    os.environ["DD_ENV"] = "demo"
    os.environ["ORCHESTRA_PIPELINE_RUN_ID"] = "abc"
    assert dd.tags(task_name="dbt", integration="") == (
        "env:demo,orchestra_pipeline_run_id:abc,task_name:dbt"
    )


if __name__ == "__main__":
    for name, check in sorted(globals().items()):
        if name.startswith("test_"):
            check()
            print(f"ok {name}")
