"""Run the Linear cycles -> MotherDuck dlt pipeline.

Environment variables consumed:
    LINEAR_API_KEY                       Linear personal API key.
    MOTHERDUCK_API_TOKEN                 MotherDuck service token (alias of MOTHERDUCK_TOKEN).
    LINEAR_CYCLES_SINCE_DAYS             Lookback window in days for ``updatedAt`` (default 7).
    LINEAR_CYCLES_MD_STAGING_DATABASE    MotherDuck staging database (default ``my_db_staging``).
    LINEAR_CYCLES_MD_DATASET             Target schema / dlt dataset_name (default ``dlt_linear_cycles``).
"""

import os

import dlt
from dlt.destinations import motherduck

from linear_cycles import linear_cycles_source


def run_pipeline(since_days: int = 7) -> None:
    api_key = os.environ.get("LINEAR_API_KEY")
    if not api_key:
        raise EnvironmentError("LINEAR_API_KEY must be set.")

    token = os.environ.get("MOTHERDUCK_API_TOKEN") or os.environ.get(
        "MOTHERDUCK_TOKEN"
    )
    if not token:
        raise EnvironmentError(
            "MOTHERDUCK_API_TOKEN (or MOTHERDUCK_TOKEN) must be set."
        )

    database = os.environ.get("LINEAR_CYCLES_MD_STAGING_DATABASE", "my_db_staging")
    dataset = os.environ.get("LINEAR_CYCLES_MD_DATASET", "dlt_linear_cycles")

    destination = motherduck(
        credentials={"database": database, "password": token},
    )

    pipeline = dlt.pipeline(
        pipeline_name="linear_cycles",
        dataset_name=dataset,
        destination=destination,
    )

    source = linear_cycles_source(api_key=api_key, since_days=since_days)
    info = pipeline.run(source)
    print(info)


if __name__ == "__main__":
    days = int(os.getenv("LINEAR_CYCLES_SINCE_DAYS", "7"))
    run_pipeline(since_days=days)
