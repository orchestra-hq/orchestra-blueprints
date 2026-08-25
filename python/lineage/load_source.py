"""Load one platform's metadata into BigQuery with dlt.

This is the entrypoint the Orchestra MetaEngine task runs once per matrix item:
the task group is expanded over `["lightdash", "bigquery", "fivetran"]` and each
child sets `LINEAGE_SOURCE` to its own value, so the three extracts run in
parallel as sibling task runs.

    LINEAGE_SOURCE=lightdash python -m load_source

Each source gets its own dlt pipeline name so the parallel children never share
dlt state.
"""

import os
import sys

import dlt
from config import (
    BQ_LOCATION,
    KNOWN_SOURCES,
    RAW_DATASET,
    ensure_google_credentials,
    resolved_bq_project,
)


def build_source(name: str):
    """Import lazily so a missing optional dependency only breaks its own source."""
    if name == "lightdash":
        from sources.lightdash import lightdash_source

        project_uuids = [
            uuid.strip()
            for uuid in os.environ.get("LIGHTDASH_PROJECT_UUIDS", "").split(",")
            if uuid.strip()
        ]
        return lightdash_source(project_uuids=project_uuids or None)

    if name == "bigquery":
        from sources.bigquery import bigquery_source

        return bigquery_source()

    if name == "fivetran":
        from sources.fivetran import fivetran_source

        return fivetran_source()

    raise ValueError(f"unknown source {name!r}, expected one of {KNOWN_SOURCES}")


def run(name: str) -> None:
    ensure_google_credentials()
    project = resolved_bq_project()

    pipeline = dlt.pipeline(
        pipeline_name=f"platform_lineage_{name}",
        destination=dlt.destinations.bigquery(location=BQ_LOCATION),
        dataset_name=RAW_DATASET,
    )
    print(f"loading {name} metadata into {project}.{RAW_DATASET}")
    print(pipeline.run(build_source(name)))


if __name__ == "__main__":
    source = (
        (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("LINEAGE_SOURCE", ""))
        .strip()
        .lower()
    )

    if not source:
        print(
            "set LINEAGE_SOURCE (or pass it as an argument) to one of: "
            + ", ".join(KNOWN_SOURCES),
            file=sys.stderr,
        )
        sys.exit(2)

    run(source)
