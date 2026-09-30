import argparse
from datetime import datetime, timedelta, timezone

import dlt
from dlt.sources.helpers.rest_client.paginators import PageNumberPaginator
from dlt.sources.rest_api import rest_api_resources, rest_api_source

# The Orchestra API caps time_from/time_to to a 7-day window per request, and
# time_from cannot be earlier than 2023-01-01.
MAX_BACKFILL_WINDOW_DAYS = 7
EARLIEST_BACKFILL_DATE = datetime(2023, 1, 1, tzinfo=timezone.utc)
TIME_FILTERED_RESOURCES = ("pipeline_runs", "task_runs", "operations")
# Re-read a few minutes before the previous run's cut-off, so a row committed
# just after that cut-off is not missed. The merge write disposition dedupes it.
WINDOW_OVERLAP = timedelta(minutes=5)
# The API filters operations on when they were inserted, but cost figures are
# written onto an operation after that, so operations are re-read for a day.
OPERATIONS_LOOKBACK = timedelta(days=1)


def _time_filtered_resource(
    name: str, time_from: str | None = None, time_to: str | None = None
) -> dict:
    endpoint = {"paginator": PageNumberPaginator(base_page=1)}
    if time_from is not None:
        endpoint["params"] = {"time_from": time_from, "time_to": time_to}
    return {"name": name, "endpoint": endpoint}


def _orchestra_api_config(
    include_assets: bool = True,
    windows: dict[str, tuple[str, str]] | None = None,
) -> dict:
    resources = [
        _time_filtered_resource(name, *(windows or {}).get(name, (None, None)))
        for name in TIME_FILTERED_RESOURCES
    ]
    if include_assets:
        resources.append(
            {
                "name": "assets",
                "endpoint": {
                    "paginator": PageNumberPaginator(base_page=1),
                },
                "primary_key": "assetId",
            }
        )

    return {
        "client": {
            "base_url": "https://app.getorchestra.io/api/engine/public/",
            "auth": {
                "type": "bearer",
                "token": dlt.secrets["orchestra_api_token"],
            },
        },
        "resource_defaults": {
            "write_disposition": "merge",
            "endpoint": {
                "params": {
                    "page_size": 100,
                },
            },
            "primary_key": "id",
        },
        "resources": resources,
    }


def build_orchestra_api_source(
    include_assets: bool = True,
    time_from: str | None = None,
    time_to: str | None = None,
):
    windows = (
        {name: (time_from, time_to) for name in TIME_FILTERED_RESOURCES}
        if time_from is not None
        else None
    )
    return rest_api_source(_orchestra_api_config(include_assets, windows))


# Named like rest_api_source so every load shares one dlt schema.
@dlt.source(name="rest_api")
def orchestra_metadata_since_last_run():
    """pipeline_runs/task_runs/operations changed since the previous successful run,
    plus a full snapshot of assets.

    The window's end is kept in dlt source state, which dlt stores in the destination,
    so it survives the fresh container each Orchestra task runs in. A failed load does
    not advance it, so the next run re-reads the same window.
    """
    state = dlt.current.source_state()
    time_to = datetime.now(timezone.utc)
    earliest_time_from = time_to - timedelta(days=MAX_BACKFILL_WINDOW_DAYS)

    if "time_to" in state:
        time_from = datetime.fromisoformat(state["time_to"]) - WINDOW_OVERLAP
        if time_from < earliest_time_from:
            print(
                f"The last successful load ended at {state['time_to']}, more than "
                f"{MAX_BACKFILL_WINDOW_DAYS} days ago. Loading the last "
                f"{MAX_BACKFILL_WINDOW_DAYS} days only; run with --backfill-days to fill the gap."
            )
            time_from = earliest_time_from
    else:
        time_from = earliest_time_from

    print(
        f"Loading pipeline_runs/task_runs/operations: {time_from.isoformat()} -> {time_to.isoformat()}"
    )

    # dlt only commits state written while a resource is extracted, not in the source body.
    @dlt.resource
    def advance_load_window():
        dlt.current.source_state()["time_to"] = time_to.isoformat()
        yield from ()

    windows = {
        name: (time_from.isoformat(), time_to.isoformat())
        for name in TIME_FILTERED_RESOURCES
    }
    windows["operations"] = (
        max(time_from - OPERATIONS_LOOKBACK, earliest_time_from).isoformat(),
        time_to.isoformat(),
    )
    return [
        *rest_api_resources(_orchestra_api_config(True, windows)),
        advance_load_window,
    ]


def _backfill_windows(days: int):
    """Yield (time_from, time_to) ISO 8601 windows covering the last `days` days,
    newest first, each spanning at most MAX_BACKFILL_WINDOW_DAYS (the API limit)."""
    window_end = datetime.now(timezone.utc)
    earliest_start = max(window_end - timedelta(days=days), EARLIEST_BACKFILL_DATE)

    while window_end > earliest_start:
        window_start = max(
            window_end - timedelta(days=MAX_BACKFILL_WINDOW_DAYS), earliest_start
        )
        yield window_start.isoformat(), window_end.isoformat()
        window_end = window_start


def orchestra_metadata_api_dlt_pipeline(warehouse: str, backfill_days: int = 0) -> None:
    pipeline = dlt.pipeline(
        pipeline_name="orchestra_metadata",
        destination=warehouse,
        dataset_name="orchestra_metadata_app",
    )

    if backfill_days > 0:
        for time_from, time_to in _backfill_windows(backfill_days):
            print(
                f"Backfilling pipeline_runs/task_runs/operations: {time_from} -> {time_to}"
            )
            source = build_orchestra_api_source(
                include_assets=False, time_from=time_from, time_to=time_to
            )
            load_info = pipeline.run(source)
            print(load_info)

    # Each Orchestra task runs in a fresh container, so restore the previous run's
    # state from the destination before reading it.
    pipeline.sync_destination()
    load_info = pipeline.run(orchestra_metadata_since_last_run())
    print(load_info)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Load Orchestra metadata into a warehouse via dlt.",
    )
    parser.add_argument(
        "warehouse",
        help="Destination warehouse (e.g. snowflake, bigquery, mssql, motherduck).",
    )
    parser.add_argument(
        "--backfill-days",
        type=int,
        default=0,
        help=(
            "Number of days of pipeline_runs/task_runs/operations history to backfill "
            f"before the standard load. Chunked automatically into {MAX_BACKFILL_WINDOW_DAYS}"
            "-day requests to respect the Orchestra API's time window limit. "
            "Defaults to 0 (no backfill)."
        ),
    )
    args = parser.parse_args()

    orchestra_metadata_api_dlt_pipeline(
        args.warehouse, backfill_days=args.backfill_days
    )
