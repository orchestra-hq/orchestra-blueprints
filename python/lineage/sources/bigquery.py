"""Extract BigQuery metadata straight from INFORMATION_SCHEMA.

Two resources:

* `bigquery_tables`  -- the asset inventory (every table and view in the project).
* `bigquery_job_edges` -- real table-to-table lineage. BigQuery records the
  `referenced_tables` and `destination_table` of every query job, so dbt/dlt/etc.
  writes become edges without anyone parsing SQL. This needs
  `bigquery.jobs.listAll`; when the credential lacks it we fall back to the
  caller's own jobs, and if that fails too the resource yields nothing rather
  than failing the load (the inventory is still worth having).
"""

import os
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

    return tables, job_edges
