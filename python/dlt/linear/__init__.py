"""Linear source for dlt.

Fetches issues from the Linear GraphQL API. The ``issues`` resource is filtered
server-side by ``updatedAt`` so callers can request only a recent window
(e.g. the last 7 days) without scanning the entire workspace.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterator, Optional

import dlt
from dlt.sources.helpers import requests


LINEAR_API_URL = "https://api.linear.app/graphql"

ISSUES_QUERY = """
query Issues($filter: IssueFilter, $after: String) {
  issues(filter: $filter, first: 100, after: $after, orderBy: updatedAt) {
    pageInfo { hasNextPage endCursor }
    nodes {
      id
      identifier
      number
      title
      description
      priority
      priorityLabel
      estimate
      sortOrder
      startedAt
      completedAt
      canceledAt
      createdAt
      updatedAt
      archivedAt
      dueDate
      url
      branchName
      state { id name type color }
      team { id key name }
      creator { id name email }
      assignee { id name email }
      project { id name state }
      cycle { id number name }
      parent { id identifier }
      labels { nodes { id name color } }
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


@dlt.source(name="linear")
def linear_source(
    api_key: str = dlt.secrets.value,
    since_days: Optional[int] = 7,
):
    """Linear dlt source.

    Args:
        api_key: Linear personal API key (header: ``Authorization: <key>``).
        since_days: Only emit issues whose ``updatedAt`` is within this many
            days. Pass ``None`` to fetch the full history.
    """

    @dlt.resource(
        name="issues",
        write_disposition="merge",
        primary_key="id",
    )
    def issues() -> Iterator[Dict[str, Any]]:
        variables: Dict[str, Any] = {"after": None}
        if since_days is not None:
            since = datetime.now(timezone.utc) - timedelta(days=since_days)
            variables["filter"] = {"updatedAt": {"gte": since.isoformat()}}

        while True:
            data = _post(api_key, ISSUES_QUERY, variables)
            page = data["issues"]
            for node in page["nodes"]:
                node["labels"] = (node.get("labels") or {}).get("nodes", [])
                yield node
            if not page["pageInfo"]["hasNextPage"]:
                break
            variables["after"] = page["pageInfo"]["endCursor"]

    return issues
