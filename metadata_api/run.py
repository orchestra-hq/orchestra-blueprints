import argparse
from datetime import datetime, timedelta, timezone

import dlt
from dlt.sources.rest_api import rest_api_source
from dlt.sources.helpers.rest_client.paginators import PageNumberPaginator

# The Orchestra API caps time_from/time_to to a 7-day window per request, and
# time_from cannot be earlier than 2023-01-01.
MAX_BACKFILL_WINDOW_DAYS = 7
EARLIEST_BACKFILL_DATE = datetime(2023, 1, 1, tzinfo=timezone.utc)
TIME_FILTERED_RESOURCES = ("pipeline_runs", "task_runs", "operations")


def _time_filtered_resource(name: str, time_from: str = None, time_to: str = None) -> dict:
    endpoint = {"paginator": PageNumberPaginator(base_page=1)}
    if time_from is not None:
        endpoint["params"] = {"time_from": time_from, "time_to": time_to}
    return {"name": name, "endpoint": endpoint}


def build_orchestra_api_source(
    include_assets: bool = True,
    time_from: str = None,
    time_to: str = None,
):
    resources = [
        _time_filtered_resource(name, time_from, time_to) for name in TIME_FILTERED_RESOURCES
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

    return rest_api_source(
        {
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
    )


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
            print(f"Backfilling pipeline_runs/task_runs/operations: {time_from} -> {time_to}")
            source = build_orchestra_api_source(
                include_assets=False, time_from=time_from, time_to=time_to
            )
            load_info = pipeline.run(source)
            print(load_info)

    # Standard load: last 7 days of pipeline_runs/task_runs/operations (the API
    # default when no time window is passed), plus a full snapshot of assets
    # (which has no time filter). write_disposition="merge" makes this and any
    # backfill runs above idempotent to re-run.
    load_info = pipeline.run(build_orchestra_api_source(include_assets=True))
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

    orchestra_metadata_api_dlt_pipeline(args.warehouse, backfill_days=args.backfill_days)
