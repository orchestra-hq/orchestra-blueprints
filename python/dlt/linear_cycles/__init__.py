"""Linear cycles + issues source for dlt.

Fetches cycles and issues from the Linear GraphQL API. Both resources are
filtered server-side by ``updatedAt`` so callers can request only a recent
window (e.g. the last 12 weeks) without scanning the entire workspace.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterator, Optional

import dlt
from dlt.sources.helpers import requests


LINEAR_API_URL = "https://api.linear.app/graphql"

CYCLES_QUERY = """
query Cycles($filter: CycleFilter, $after: String) {
  cycles(filter: $filter, first: 100, after: $after) {
    pageInfo { hasNextPage endCursor }
    nodes {
      id
      number
      name
      description
      startsAt
      endsAt
      completedAt
      autoArchivedAt
      archivedAt
      createdAt
      updatedAt
      progress
      scopeHistory
      completedScopeHistory
      inProgressScopeHistory
      issueCountHistory
      completedIssueCountHistory
      team { id key name }
    }
  }
}
"""

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


@dlt.source(name="linear_cycles")
def linear_cycles_source(
    api_key: str = dlt.secrets.value,
    since_days: Optional[int] = 84,
):
    """Linear cycles + issues dlt source.

    Args:
        api_key: Linear personal API key (header: ``Authorization: <key>``).
        since_days: Only emit records whose ``updatedAt`` is within this many
            days. Pass ``None`` to fetch the full history.
    """

    def _since_filter() -> Optional[Dict[str, Any]]:
        if since_days is None:
            return None
        since = datetime.now(timezone.utc) - timedelta(days=since_days)
        return {"updatedAt": {"gte": since.isoformat()}}

    @dlt.resource(
        name="cycles",
        write_disposition="merge",
        primary_key="id",
    )
    def cycles() -> Iterator[Dict[str, Any]]:
        variables: Dict[str, Any] = {"after": None}
        filt = _since_filter()
        if filt is not None:
            variables["filter"] = filt

        while True:
            data = _post(api_key, CYCLES_QUERY, variables)
            page = data["cycles"]
            for node in page["nodes"]:
                yield node
            if not page["pageInfo"]["hasNextPage"]:
                break
            variables["after"] = page["pageInfo"]["endCursor"]

    @dlt.resource(
        name="issues",
        write_disposition="merge",
        primary_key="id",
    )
    def issues() -> Iterator[Dict[str, Any]]:
        variables: Dict[str, Any] = {"after": None}
        filt = _since_filter()
        if filt is not None:
            variables["filter"] = filt

        while True:
            data = _post(api_key, ISSUES_QUERY, variables)
            page = data["issues"]
            for node in page["nodes"]:
                node["labels"] = (node.get("labels") or {}).get("nodes", [])
                yield node
            if not page["pageInfo"]["hasNextPage"]:
                break
            variables["after"] = page["pageInfo"]["endCursor"]

    return cycles, issues
