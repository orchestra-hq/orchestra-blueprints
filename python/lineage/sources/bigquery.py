"""Extract BigQuery metadata straight from INFORMATION_SCHEMA.

Two resources:

* `bigquery_tables`  -- the asset inventory (every table and view in the project).
* `bigquery_job_edges` -- table-to-table lineage from job history. BigQuery
  records the `referenced_tables` and `destination_table` of every query job, so
  dbt/dlt/etc. writes become edges without anyone parsing SQL. This is the best
  source of warehouse lineage but it needs `bigquery.jobs.listAll`; when the
  credential lacks it we fall back to the caller's own jobs, and if that fails
  too the resource yields nothing rather than failing the load.
* `bigquery_view_refs` -- the fallback for the above. Every table a view selects
  from, taken from the view's own SQL. It needs no extra IAM beyond reading
  INFORMATION_SCHEMA, so the graph still has warehouse edges on a credential
  that cannot list jobs.
"""

import os
import re
from typing import Any, Iterator

import dlt
from google.cloud import bigquery

from config import resolved_bq_project, BQ_LOCATION

# INFORMATION_SCHEMA is region-scoped: one query covers every dataset in the
# region, which beats iterating datasets one at a time.
_TABLES_SQL = """
SELECT
  table_catalog,
  table_schema,
  table_name,
  table_type,
  creation_time,
  ddl
FROM `{project}`.`region-{location}`.INFORMATION_SCHEMA.TABLES
"""

# `job_type = 'QUERY'` with a destination table is the set of writes. Anonymous
# result caches (`_script`/`anon` datasets) are noise and get filtered out.
_JOB_EDGES_SQL = """
SELECT
  job_id,
  creation_time,
  destination_table.project_id AS destination_project,
  destination_table.dataset_id AS destination_dataset,
  destination_table.table_id   AS destination_table,
  referenced.project_id        AS source_project,
  referenced.dataset_id        AS source_dataset,
  referenced.table_id          AS source_table
FROM `{project}`.`region-{location}`.INFORMATION_SCHEMA.{view}
CROSS JOIN UNNEST(referenced_tables) AS referenced
WHERE job_type = 'QUERY'
  AND state = 'DONE'
  AND error_result IS NULL
  AND destination_table.table_id IS NOT NULL
  AND NOT STARTS_WITH(destination_table.dataset_id, '_')
  AND creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
"""


_VIEWS_SQL = """
SELECT
  table_catalog,
  table_schema,
  table_name,
  view_definition
FROM `{project}`.`region-{location}`.INFORMATION_SCHEMA.VIEWS
WHERE view_definition IS NOT NULL
"""

# BigQuery view SQL refers to tables as `project.dataset.table` (or
# `project`.`dataset`.`table`), so the fully-qualified backticked reference is a
# reliable thing to pull out -- no general SQL parsing required.
_REFERENCE_PATTERN = re.compile(
    r"`(?P<project>[\w-]+)`?\.`?(?P<dataset>\w+)`?\.`?(?P<table>\w+)`"
)


def _rows(client: bigquery.Client, sql: str) -> Iterator[dict[str, Any]]:
    for row in client.query(sql, location=BQ_LOCATION).result():
        yield dict(row.items())


@dlt.source(name="bigquery")
def bigquery_source() -> Any:
    """Table inventory plus job-derived table-to-table edges."""

    project = resolved_bq_project()
    lookback_days = int(os.environ.get("LINEAGE_BQ_LOOKBACK_DAYS", "7"))
    client = bigquery.Client(project=project)

    @dlt.resource(name="bigquery_tables", write_disposition="replace")
    def tables() -> Iterator[dict[str, Any]]:
        yield from _rows(
            client, _TABLES_SQL.format(project=project, location=BQ_LOCATION)
        )

    @dlt.resource(name="bigquery_job_edges", write_disposition="replace")
    def job_edges() -> Iterator[dict[str, Any]]:
        for view in ("JOBS_BY_PROJECT", "JOBS_BY_USER"):
            sql = _JOB_EDGES_SQL.format(
                project=project,
                location=BQ_LOCATION,
                view=view,
                days=lookback_days,
            )
            try:
                yield from _rows(client, sql)
                return
            except Exception as exc:  # noqa: BLE001 - permissions vary by credential
                print(f"bigquery_job_edges: {view} unavailable ({exc})")
        print("bigquery_job_edges: no job history readable, yielding no edges")

    @dlt.resource(name="bigquery_view_refs", write_disposition="replace")
    def view_refs() -> Iterator[dict[str, Any]]:
        for view in _rows(
            client, _VIEWS_SQL.format(project=project, location=BQ_LOCATION)
        ):
            seen: set[tuple[str, str, str]] = set()
            for match in _REFERENCE_PATTERN.finditer(view["view_definition"]):
                reference = (
                    match.group("project"),
                    match.group("dataset"),
                    match.group("table"),
                )
                if reference in seen:
                    continue
                seen.add(reference)
                yield {
                    "view_project": view["table_catalog"],
                    "view_dataset": view["table_schema"],
                    "view_name": view["table_name"],
                    "source_project": reference[0],
                    "source_dataset": reference[1],
                    "source_table": reference[2],
                }

    return tables, job_edges, view_refs
