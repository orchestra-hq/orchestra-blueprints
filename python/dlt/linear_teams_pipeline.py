"""Run the Linear teams -> MotherDuck dlt pipeline.

Environment variables consumed:
    LINEAR_API_KEY                      Linear personal API key.
    MOTHERDUCK_API_TOKEN                MotherDuck service token (alias of MOTHERDUCK_TOKEN).
    LINEAR_TEAMS_SINCE_DAYS             Lookback window in days for ``updatedAt`` (default unset = full load).
    LINEAR_TEAMS_MD_STAGING_DATABASE   MotherDuck staging database (default ``my_db_staging``).
    LINEAR_TEAMS_MD_DATASET            Target schema / dlt dataset_name (default ``dlt_linear_teams``).
"""

import os
from typing import Optional

import dlt
from dlt.destinations import motherduck

from linear_teams import linear_teams_source


def run_pipeline(since_days: Optional[int] = None) -> None:
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

    database = os.environ.get("LINEAR_TEAMS_MD_STAGING_DATABASE", "my_db_staging")
    dataset = os.environ.get("LINEAR_TEAMS_MD_DATASET", "dlt_linear_teams")

    destination = motherduck(
        credentials={"database": database, "password": token},
    )

    pipeline = dlt.pipeline(
        pipeline_name="linear_teams",
        dataset_name=dataset,
        destination=destination,
    )

    source = linear_teams_source(api_key=api_key, since_days=since_days)
    info = pipeline.run(source)
    print(info)


if __name__ == "__main__":
    raw = os.getenv("LINEAR_TEAMS_SINCE_DAYS")
    days = int(raw) if raw not in (None, "") else None
    run_pipeline(since_days=days)
