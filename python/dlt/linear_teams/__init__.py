"""Linear teams source for dlt.

Fetches teams from the Linear GraphQL API. Teams are a small workspace
dimension, so by default the resource performs a full load (``since_days=None``).
Pass ``since_days`` to filter server-side by ``updatedAt`` if only a recent
window is wanted.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterator, Optional

import dlt
from dlt.sources.helpers import requests


LINEAR_API_URL = "https://api.linear.app/graphql"

TEAMS_QUERY = """
query Teams($filter: TeamFilter, $after: String) {
  teams(filter: $filter, first: 100, after: $after) {
    pageInfo { hasNextPage endCursor }
    nodes {
      id
      key
      name
      description
      private
      icon
      color
      timezone
      cyclesEnabled
      cycleDuration
      cycleStartDay
      issueEstimationType
      issueEstimationAllowZero
      issueEstimationExtended
      defaultIssueEstimate
      autoArchivePeriod
      autoClosePeriod
      createdAt
      updatedAt
      archivedAt
    }
  }
}
"""


def _post(api_key: str, query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
    response = requests.post(
        LINEAR_API_URL,
        json={"query": query, "variables": variables},
        headers={"Authorization": api_key, "Content-Type": "application/json"},
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("errors"):
        raise RuntimeError(f"Linear API error: {payload['errors']}")
    return payload["data"]


@dlt.source(name="linear_teams")
def linear_teams_source(
    api_key: str = dlt.secrets.value,
    since_days: Optional[int] = None,
):
    """Linear teams dlt source.

    Args:
        api_key: Linear personal API key (header: ``Authorization: <key>``).
        since_days: Only emit teams whose ``updatedAt`` is within this many
            days. Pass ``None`` (the default) to fetch every team.
    """

    @dlt.resource(
        name="teams",
        write_disposition="merge",
        primary_key="id",
    )
    def teams() -> Iterator[Dict[str, Any]]:
        variables: Dict[str, Any] = {"after": None}
        if since_days is not None:
            since = datetime.now(timezone.utc) - timedelta(days=since_days)
            variables["filter"] = {"updatedAt": {"gte": since.isoformat()}}

        while True:
            data = _post(api_key, TEAMS_QUERY, variables)
            page = data["teams"]
            for node in page["nodes"]:
                yield node
            if not page["pageInfo"]["hasNextPage"]:
                break
            variables["after"] = page["pageInfo"]["endCursor"]

    return teams
