"""Extract Fivetran metadata: groups, connectors and their destination tables.

Fivetran is the left-hand edge of the lineage graph -- each connector writes into
a warehouse schema, so `fivetran_connectors` joined to `fivetran_destinations`
gives the `connector -> project.dataset` edge that Orchestra draws from a
Fivetran asset into a BigQuery one.
"""

import base64
from typing import Any, Iterator

import dlt
from dlt.sources.helpers import requests

from config import is_skippable, require_env

_BASE_URL = "https://api.fivetran.com/v1"
_TIMEOUT = 60


def _headers() -> dict[str, str]:
    key, secret = require_env("FIVETRAN_API_KEY", "FIVETRAN_API_SECRET")
    token = base64.b64encode(f"{key}:{secret}".encode()).decode()
    return {"Authorization": f"Basic {token}", "Accept": "application/json"}


def _get(path: str) -> Any:
    """Single GET returning the `data` envelope."""
    response = requests.get(f"{_BASE_URL}/{path}", headers=_headers(), timeout=_TIMEOUT)
    response.raise_for_status()
    return response.json().get("data") or {}


def _paginate(path: str) -> Iterator[dict[str, Any]]:
    """Walk Fivetran's cursor pagination over a collection endpoint."""
    cursor: str | None = None
    while True:
        suffix = f"?cursor={cursor}" if cursor else ""
        data = _get(f"{path}{suffix}")
        yield from data.get("items") or []
        cursor = data.get("next_cursor")
        if not cursor:
            return


@dlt.source(name="fivetran")
def fivetran_source() -> Any:
    """Groups, their destinations, and every connector inside them."""

    groups = list(_paginate("groups"))

    @dlt.resource(name="fivetran_groups", write_disposition="replace")
    def group_rows() -> Iterator[dict[str, Any]]:
        yield from groups

    @dlt.resource(name="fivetran_destinations", write_disposition="replace")
    def destinations() -> Iterator[dict[str, Any]]:
        """Where each group lands. `config.project_id` is the BigQuery project."""
        for group in groups:
            # A group without a configured destination 404s here. Keep the row so
            # the group is still recorded; the null warehouse fields mean it
            # simply contributes no edge.
            try:
                destination = _get(f"destinations/{group['id']}")
            except requests.HTTPError as exc:
                if not is_skippable(exc):
                    raise
                print(
                    f"fivetran_destinations: no destination for {group['id']} ({exc})"
                )
                destination = {}
            config = destination.get("config") or {}
            yield {
                "group_id": group["id"],
                "group_name": group.get("name"),
                "service": destination.get("service"),
                "region": destination.get("region"),
                "warehouse_project": config.get("project_id"),
                "warehouse_dataset": config.get("data_set_location")
                or config.get("dataset"),
                "warehouse_location": config.get("location")
                or config.get("data_set_location"),
            }

    @dlt.resource(name="fivetran_connectors", write_disposition="replace")
    def connectors() -> Iterator[dict[str, Any]]:
        for group in groups:
            try:
                group_connectors = list(_paginate(f"groups/{group['id']}/connectors"))
            except requests.HTTPError as exc:
                if not is_skippable(exc):
                    raise
                print(f"fivetran_connectors: cannot list group {group['id']} ({exc})")
                continue
            for connector in group_connectors:
                config = connector.get("config") or {}
                status = connector.get("status") or {}
                yield {
                    "connector_id": connector.get("id"),
                    "group_id": group["id"],
                    "group_name": group.get("name"),
                    "service": connector.get("service"),
                    # The connector's destination schema in the warehouse.
                    "connector_schema": connector.get("schema") or config.get("schema"),
                    "table": config.get("table"),
                    "setup_state": status.get("setup_state"),
                    "sync_state": status.get("sync_state"),
                    "succeeded_at": connector.get("succeeded_at"),
                    "created_at": connector.get("created_at"),
                    "paused": connector.get("paused"),
                }

    return group_rows, destinations, connectors
