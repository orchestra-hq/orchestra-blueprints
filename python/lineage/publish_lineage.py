"""Publish the dbt-built lineage marts into Orchestra.

Reads `lineage_assets` and `lineage_edges` out of BigQuery and pushes them to
Orchestra's metadata API:

    POST /assets               -- register/refresh each asset
    POST /assets/dependencies  -- create the directed lineage edges

Both are idempotent by design. Assets are keyed on `externalId`, so anything
Orchestra already collected itself (a BigQuery table, a Lightdash chart) is
PATCHed rather than duplicated, and edges are re-sent harmlessly.

    ORCHESTRA_API_KEY=... python -m publish_lineage
    python -m publish_lineage --dry-run   # print what would be sent, send nothing
"""

import os
import sys
import time
from typing import Any, Iterable, Iterator

import requests
from google.cloud import bigquery
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import (
    BQ_LOCATION,
    MART_DATASET,
    ensure_google_credentials,
    require_env,
    resolved_bq_project,
)

API_BASE = os.environ.get(
    "ORCHESTRA_API_BASE", "https://app.getorchestra.io/api/engine/public"
).rstrip("/")

# The dependencies endpoint accepts at most 100 edges per request.
EDGE_BATCH_SIZE = 100
_TIMEOUT = 120

# Orchestra's metadata API allows 50 requests/minute. Assets are written one at
# a time (there's no bulk-upsert endpoint), so a workspace with a few hundred
# assets already takes minutes; pacing calls at a safe fraction of the limit
# converges without burning most of them on 429s and their retries.
_REQUESTS_PER_MINUTE = 50
_PACING_SECONDS = 60 / _REQUESTS_PER_MINUTE * 1.25
_PROGRESS_EVERY = 25


def _session() -> requests.Session:
    (api_key,) = require_env("ORCHESTRA_API_KEY")
    session = requests.Session()
    session.headers.update(
        {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    )
    # Safety net under the pacing above: a burst from another concurrent job
    # against the same API key can still trip the limit. Retry 429s and 5xxs
    # with backoff; honour Retry-After when Orchestra sends one.
    retry = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "POST", "PATCH"}),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _read_table(client: bigquery.Client, table: str) -> list[dict[str, Any]]:
    project = resolved_bq_project()
    sql = f"SELECT * FROM `{project}`.`{MART_DATASET}`.`{table}`"
    return [
        dict(row.items()) for row in client.query(sql, location=BQ_LOCATION).result()
    ]


def _existing_assets(session: requests.Session) -> dict[str, str]:
    """Map every asset already in the workspace from externalId to assetId.

    The list endpoint has no externalId filter, so we page the whole workspace
    once. That is far cheaper than eating a 409 per asset and it tells us which
    assets to PATCH instead of POST.
    """
    mapping: dict[str, str] = {}
    page = 1
    while True:
        response = session.get(
            f"{API_BASE}/assets",
            params={"page": page, "page_size": 100},
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results") or []
        for asset in results:
            if asset.get("externalId"):
                mapping[asset["externalId"]] = asset["assetId"]
        if len(mapping) >= payload.get("total", 0) or not results:
            return mapping
        page += 1


def _iso(value: Any) -> str | None:
    return value.isoformat() if hasattr(value, "isoformat") else value


def _asset_body(row: dict[str, Any]) -> dict[str, Any]:
    body = {
        "assetName": row["asset_name"],
        "externalId": row["external_id"],
        "integration": row["integration"],
        "integrationAccountId": row["integration_account_id"],
        "assetType": row.get("asset_type") or "UNKNOWN",
        "databaseName": row.get("database_name"),
        "schemaName": row.get("schema_name"),
        "tableName": row.get("table_name"),
        "workspaceName": row.get("workspace_name"),
        "description": row.get("description"),
        "url": row.get("url"),
        "createdInIntegration": _iso(row.get("created_in_integration")),
        "meta": {"source": "orchestra-blueprints/platform-lineage"},
    }
    return {key: value for key, value in body.items() if value is not None}


def _batched(items: list[Any], size: int) -> Iterator[list[Any]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def publish_assets(
    session: requests.Session, rows: Iterable[dict[str, Any]], dry_run: bool
) -> tuple[int, int, int]:
    """Create assets Orchestra has not seen and PATCH the ones it has."""
    existing = {} if dry_run else _existing_assets(session)
    created = updated = failed = 0

    for index, row in enumerate(rows, start=1):
        body = _asset_body(row)
        external_id = body["externalId"]
        asset_id = existing.get(external_id)

        if dry_run:
            print(f"  would publish {body['integration']:<14} {external_id}")
            created += 1
            continue

        if asset_id:
            # PATCH only accepts the mutable descriptive fields.
            patch = {
                key: value
                for key, value in body.items()
                if key
                in {
                    "databaseName",
                    "schemaName",
                    "tableName",
                    "workspaceName",
                    "description",
                    "url",
                    "createdInIntegration",
                    "meta",
                }
            }
            response = session.patch(
                f"{API_BASE}/assets/{asset_id}", json=patch, timeout=_TIMEOUT
            )
        else:
            response = session.post(f"{API_BASE}/assets", json=body, timeout=_TIMEOUT)

        # Stay under the 50/minute limit rather than lean on the retry adapter
        # for the common case -- it exists as a safety net, not the plan.
        time.sleep(_PACING_SECONDS)
        if index % _PROGRESS_EVERY == 0:
            print(
                f"  ...{index} assets processed (created={created} updated={updated} failed={failed})"
            )

        if response.status_code in (200, 201):
            created += 0 if asset_id else 1
            updated += 1 if asset_id else 0
        elif response.status_code == 409:
            # Raced with Orchestra's own collector; the asset exists, which is
            # all the edges below need.
            updated += 1
        else:
            failed += 1
            print(
                f"  FAILED {external_id}: {response.status_code} {response.text[:200]}"
            )

    return created, updated, failed


def publish_edges(
    session: requests.Session, rows: list[dict[str, Any]], dry_run: bool
) -> tuple[int, int]:
    edges = [
        {
            "fromId": row["from_external_id"],
            "toId": row["to_external_id"],
            "lineageDetail": row["lineage_detail"],
            "integration": row["integration"],
        }
        for row in rows
    ]

    if dry_run:
        for edge in edges:
            print(f"  would link {edge['fromId']} -> {edge['toId']}")
        return len(edges), 0

    created = failed = 0
    for batch in _batched(edges, EDGE_BATCH_SIZE):
        response = session.post(
            f"{API_BASE}/assets/dependencies",
            json={"dependencies": batch},
            timeout=_TIMEOUT,
        )
        if response.status_code in (200, 201):
            created += response.json().get("created", len(batch))
        else:
            failed += len(batch)
            print(f"  FAILED edge batch: {response.status_code} {response.text[:300]}")
    return created, failed


def main(dry_run: bool) -> int:
    ensure_google_credentials()
    client = bigquery.Client(project=resolved_bq_project())

    assets = _read_table(client, "lineage_assets")
    edges = _read_table(client, "lineage_edges")
    print(f"read {len(assets)} assets and {len(edges)} edges from {MART_DATASET}")

    session = None if dry_run else _session()

    print("publishing assets...")
    created, updated, asset_failures = publish_assets(session, assets, dry_run)
    print(f"  created={created} updated={updated} failed={asset_failures}")

    print("publishing lineage edges...")
    edges_created, edge_failures = publish_edges(session, edges, dry_run)
    print(f"  created={edges_created} failed={edge_failures}")

    if asset_failures or edge_failures:
        print("some writes failed -- see the errors above", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(dry_run="--dry-run" in sys.argv))
