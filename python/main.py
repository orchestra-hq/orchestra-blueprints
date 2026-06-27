"""Fetch Power BI datasets to refresh and expose their IDs as an Orchestra output.

This script powers the "Fetch Power BI datasets to refresh" Python task in the
"Python -> dbt Core -> Power BI" pipeline. It produces a single Orchestra task
output named ``datasets`` containing a flat list of Power BI dataset IDs. A
downstream Power BI MetaEngine (matrix) task fans out over that list, refreshing
each dataset (``dataset_id: ${{ MATRIX.datasets }}``).

The dataset IDs are resolved from one of two sources, checked in order:

1. Explicit override -- set ``POWERBI_DATASET_IDS`` to a comma-separated list or
   a JSON array of dataset GUIDs. Use this when you already know exactly which
   datasets to refresh and don't want to call the Power BI REST API.

2. Power BI REST API -- if a service principal is configured via environment
   variables, the script lists the datasets in the workspace (group) and selects
   the refreshable ones.

Environment variables (REST API path):
  POWERBI_TENANT_ID      (or AZURE_TENANT_ID / TENANT_ID)
  POWERBI_CLIENT_ID      (or AZURE_CLIENT_ID / CLIENT_ID)
  POWERBI_CLIENT_SECRET  (or AZURE_CLIENT_SECRET / CLIENT_SECRET)
  POWERBI_GROUP_ID       (or POWERBI_WORKSPACE_ID / GROUP_ID / WORKSPACE_ID)  [optional]
  POWERBI_DATASET_IDS    explicit override, skips the API call                [optional]

Orchestra injects ORCHESTRA_API_KEY / ORCHESTRA_TASK_RUN_ID automatically and
pre-installs the ``orchestra-sdk`` package, so it does not need to be listed in
requirements.txt.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Optional

import requests

PBI_SCOPE = "https://analysis.windows.net/powerbi/api/.default"
PBI_API = "https://api.powerbi.com/v1.0/myorg"


def _first_env(*names: str) -> Optional[str]:
    """Return the first non-empty value among the given env var names."""
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    return None


def _ids_from_override() -> list:
    """Parse POWERBI_DATASET_IDS as a JSON array or comma-separated list."""
    raw = os.getenv("POWERBI_DATASET_IDS")
    if not raw or not raw.strip():
        return []
    raw = raw.strip()
    if raw.startswith("["):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"POWERBI_DATASET_IDS is not valid JSON: {exc}")
        return [str(x).strip() for x in parsed if str(x).strip()]
    return [part.strip() for part in raw.split(",") if part.strip()]


def _get_token(tenant: str, client_id: str, client_secret: str) -> str:
    url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
    resp = requests.post(
        url,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": PBI_SCOPE,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _list_datasets(token: str, group: Optional[str]) -> list:
    base = f"{PBI_API}/groups/{group}/datasets" if group else f"{PBI_API}/datasets"
    resp = requests.get(
        base, headers={"Authorization": f"Bearer {token}"}, timeout=60
    )
    resp.raise_for_status()
    return resp.json().get("value", [])


def _ids_from_api() -> list:
    tenant = _first_env("POWERBI_TENANT_ID", "AZURE_TENANT_ID", "TENANT_ID")
    client_id = _first_env("POWERBI_CLIENT_ID", "AZURE_CLIENT_ID", "CLIENT_ID")
    client_secret = _first_env(
        "POWERBI_CLIENT_SECRET", "AZURE_CLIENT_SECRET", "CLIENT_SECRET"
    )
    group = _first_env(
        "POWERBI_GROUP_ID", "POWERBI_WORKSPACE_ID", "GROUP_ID", "WORKSPACE_ID"
    )

    missing = [
        label
        for label, value in (
            ("tenant id", tenant),
            ("client id", client_id),
            ("client secret", client_secret),
        )
        if not value
    ]
    if missing:
        raise SystemExit(
            "No Power BI dataset source configured. Either set POWERBI_DATASET_IDS "
            "to an explicit list of dataset GUIDs, or configure a service principal "
            "on the Python connection so datasets can be fetched from the Power BI "
            "REST API (missing: " + ", ".join(missing) + ")."
        )

    token = _get_token(tenant, client_id, client_secret)
    datasets = _list_datasets(token, group)
    return [d["id"] for d in datasets if d.get("id") and d.get("isRefreshable", True)]


def _set_output(name: str, value) -> None:
    from orchestra_sdk.orchestra import OrchestraSDK

    client = OrchestraSDK(api_key=os.environ.get("ORCHESTRA_API_KEY"))
    client.set_output(name, value)


def main() -> int:
    ids = _ids_from_override()
    source = "POWERBI_DATASET_IDS override"
    if not ids:
        ids = _ids_from_api()
        source = "Power BI REST API"

    # De-duplicate while preserving order.
    seen = set()
    ids = [x for x in ids if not (x in seen or seen.add(x))]

    if not ids:
        raise SystemExit(
            "No Power BI datasets resolved to refresh. Check the workspace/group "
            "configuration or the POWERBI_DATASET_IDS override."
        )

    print(f"Resolved {len(ids)} dataset(s) to refresh via {source}: {ids}")
    _set_output("datasets", ids)
    print("Set Orchestra output 'datasets' for the downstream Power BI matrix.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
