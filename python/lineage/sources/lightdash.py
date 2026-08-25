"""Extract Lightdash metadata: projects, explores, charts and dashboards.

The lineage-bearing fact is `lightdash_chart_tables`: which warehouse table each
saved chart ultimately reads. Lightdash does not expose that directly, so we
join a chart's `metricQuery.exploreName` to the explore's base table
(`database.schema.name`), which is what Orchestra needs as the upstream
`externalId` of the chart asset.
"""

from typing import Any, Iterator

import dlt
from dlt.sources.helpers import requests

from config import is_skippable, require_env

# Lightdash wraps every response as {"status": "ok", "results": ...}.
_TIMEOUT = 60


def _client() -> tuple[str, dict[str, str]]:
    host, token = require_env(
        "TAP_LIGHTDASH_URL", "TAP_LIGHTDASH_PERSONAL_ACCESS_TOKEN"
    )
    headers = {
        "Authorization": f"ApiKey {token}",
        "Content-Type": "application/json",
    }
    return host.rstrip("/"), headers


def _get(path: str) -> Any:
    host, headers = _client()
    response = requests.get(f"{host}/api/v1/{path}", headers=headers, timeout=_TIMEOUT)
    response.raise_for_status()
    return response.json().get("results")


@dlt.source(name="lightdash")
def lightdash_source(project_uuids: list[str] | None = None) -> Any:
    """All Lightdash resources, optionally narrowed to specific projects."""

    # Fetched once and shared by every resource below: the org rarely has more
    # than a handful of projects, and each resource needs the same list.
    selected = [
        project
        for project in _get("org/projects") or []
        if not project_uuids or project["projectUuid"] in project_uuids
    ]

    @dlt.resource(name="lightdash_projects", write_disposition="replace")
    def projects() -> Iterator[dict[str, Any]]:
        yield from selected

    @dlt.resource(name="lightdash_explores", write_disposition="replace")
    def explores() -> Iterator[dict[str, Any]]:
        """Explores with their resolved warehouse base table.

        `GET /projects/{uuid}/explores` is a summary list; the per-explore
        endpoint is the only place the base table's database/schema appear, so we
        fetch each one. Explores that fail to compile in Lightdash return an
        error payload -- they are skipped rather than failing the whole load.
        """
        for project in selected:
            project_uuid = project["projectUuid"]
            for summary in _get(f"projects/{project_uuid}/explores") or []:
                name = summary.get("name")
                if not name:
                    continue
                try:
                    detail = _get(f"projects/{project_uuid}/explores/{name}")
                except requests.HTTPError as exc:
                    if not is_skippable(exc):
                        raise
                    detail = None
                base_table = (detail or {}).get("baseTable")
                table = ((detail or {}).get("tables") or {}).get(base_table) or {}
                yield {
                    "project_uuid": project_uuid,
                    "explore_name": name,
                    "explore_label": summary.get("label"),
                    "base_table": base_table,
                    "warehouse_database": table.get("database"),
                    "warehouse_schema": table.get("schema"),
                    "warehouse_table": table.get("name"),
                    "sql_table": table.get("sqlTable"),
                }

    @dlt.resource(name="lightdash_charts", write_disposition="replace")
    def charts() -> Iterator[dict[str, Any]]:
        for project in selected:
            project_uuid = project["projectUuid"]
            for chart in _get(f"projects/{project_uuid}/charts") or []:
                chart_uuid = chart.get("uuid")
                # The list endpoint can include charts the token cannot open
                # (deleted, or in a space it has no access to); `saved/{uuid}`
                # then 404s. Keep the chart as an asset, just without its
                # explore, rather than failing the whole extract.
                detail = None
                if chart_uuid:
                    try:
                        detail = _get(f"saved/{chart_uuid}")
                    except requests.HTTPError as exc:
                        print(
                            f"lightdash_charts: skipping detail for {chart_uuid} ({exc})"
                        )
                metric_query = (detail or {}).get("metricQuery") or {}
                yield {
                    "project_uuid": project_uuid,
                    "chart_uuid": chart_uuid,
                    "chart_name": chart.get("name"),
                    "description": chart.get("description"),
                    "space_uuid": chart.get("spaceUuid"),
                    "space_name": chart.get("spaceName"),
                    "updated_at": chart.get("updatedAt"),
                    # `tableName` is the explore the chart is built on.
                    "explore_name": (detail or {}).get("tableName")
                    or metric_query.get("exploreName")
                    or chart.get("tableName"),
                    "slug": (detail or {}).get("slug"),
                }

    @dlt.resource(name="lightdash_dashboards", write_disposition="replace")
    def dashboards() -> Iterator[dict[str, Any]]:
        for project in selected:
            project_uuid = project["projectUuid"]
            for dashboard in _get(f"projects/{project_uuid}/dashboards") or []:
                yield {
                    "project_uuid": project_uuid,
                    "dashboard_uuid": dashboard.get("uuid"),
                    "dashboard_name": dashboard.get("name"),
                    "description": dashboard.get("description"),
                    "space_uuid": dashboard.get("spaceUuid"),
                    "updated_at": dashboard.get("updatedAt"),
                }

    return projects, explores, charts, dashboards
