"""Collect Databricks Unity Catalog tables and views into Orchestra.

A self-run replacement for Orchestra's scheduled Databricks asset collection.
It runs the same `system.information_schema.tables` query the built-in
collector runs, then publishes each table/view through the public asset API:

    GET   /assets                -- what Orchestra already has, keyed on externalId
    POST  /assets                -- create the ones it doesn't
    PATCH /assets/{externalId}   -- refresh the ones that changed
    POST  /assets/dependencies   -- table-to-table lineage from system.access.table_lineage

External IDs follow the built-in collector's format,
`<workspace>.<catalog>.<schema>.<table>`, so assets it already collected are
updated in place rather than duplicated.

    python collect_assets.py --warehouse-id <id>
    python collect_assets.py --warehouse-id <id> --catalog main --dry-run
"""

import argparse
import logging
import os
import sys
import time
from datetime import UTC, datetime
from typing import Any

import httpx

logger = logging.getLogger("databricks_assets")

ORCHESTRA_API_BASE = os.environ.get(
    "ORCHESTRA_API_BASE", "https://app.getorchestra.io/api/engine/public"
).rstrip("/")

# Pace below Orchestra's 50 requests/minute metadata API limit so retries stay the exception.
_ORCHESTRA_SECONDS_PER_REQUEST = 60 / 50 * 1.25
_MAX_ATTEMPTS = 6
_TIMEOUT = 120
_EDGE_BATCH_SIZE = 100
_PROGRESS_EVERY = 25

_TABLES_SQL = """
SELECT table_catalog, table_schema, table_name, table_type, table_owner,
       comment, created, last_altered
FROM system.information_schema.tables
WHERE table_schema != 'information_schema'
  AND table_catalog != 'samples'
  AND table_catalog != 'system'
"""

_LINEAGE_SQL = """
SELECT DISTINCT source_table_full_name, target_table_full_name
FROM system.access.table_lineage
WHERE source_table_full_name IS NOT NULL
  AND target_table_full_name IS NOT NULL
  AND event_date >= date_sub(current_date(), :lookback_days)
"""

# Fields compared against what Orchestra holds to decide whether to PATCH.
_COMPARED_FIELDS = (
    "databaseName",
    "schemaName",
    "tableName",
    "description",
    "owners",
    "createdInIntegration",
    "lastUpdatedInIntegration",
)
_TIMESTAMP_FIELDS = {"createdInIntegration", "lastUpdatedInIntegration"}


class Databricks:
    """Runs SQL on a Databricks SQL warehouse through the Statement Execution API."""

    def __init__(self, host: str, token: str, warehouse_id: str) -> None:
        self.warehouse_id = warehouse_id
        self.client = httpx.Client(
            base_url=f"https://{host}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=_TIMEOUT,
        )

    def query(self, sql: str, parameters: list[dict] | None = None) -> list[dict]:
        response = self.client.post(
            "/api/2.0/sql/statements",
            json={
                "statement": sql,
                "warehouse_id": self.warehouse_id,
                "parameters": parameters or [],
                "wait_timeout": "30s",
                "on_wait_timeout": "CONTINUE",
            },
        )
        response.raise_for_status()
        payload = response.json()
        statement_id = payload["statement_id"]

        while payload["status"]["state"] in ("PENDING", "RUNNING"):
            logger.info("Statement %s is %s", statement_id, payload["status"]["state"])
            time.sleep(10)
            response = self.client.get(f"/api/2.0/sql/statements/{statement_id}")
            response.raise_for_status()
            payload = response.json()

        if payload["status"]["state"] != "SUCCEEDED":
            error = payload["status"].get("error", {}).get("message", "")
            raise RuntimeError(
                f"Statement {statement_id} {payload['status']['state']}: {error}"
            )

        columns = [
            column["name"] for column in payload["manifest"]["schema"]["columns"]
        ]
        result = payload.get("result", {})
        rows = list(result.get("data_array") or [])
        # Large results are split into chunks; follow them so nothing is dropped.
        while (next_chunk := result.get("next_chunk_index")) is not None:
            response = self.client.get(
                f"/api/2.0/sql/statements/{statement_id}/result/chunks/{next_chunk}"
            )
            response.raise_for_status()
            result = response.json()
            rows.extend(result.get("data_array") or [])
        return [dict(zip(columns, row)) for row in rows]


class Orchestra:
    """Paced client for Orchestra's public asset API, retrying 429s and 5xxs."""

    def __init__(self, api_key: str) -> None:
        self.client = httpx.Client(
            base_url=ORCHESTRA_API_BASE,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=_TIMEOUT,
        )

    def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        for attempt in range(1, _MAX_ATTEMPTS):
            time.sleep(_ORCHESTRA_SECONDS_PER_REQUEST)
            response = self.client.request(method, path, **kwargs)
            if response.status_code != 429 and response.status_code < 500:
                return response
            retry_after = response.headers.get("Retry-After", "")
            delay = float(retry_after) if retry_after.isdigit() else 2**attempt
            logger.warning(
                "%s %s returned %s, retrying in %ss",
                method,
                path,
                response.status_code,
                delay,
            )
            time.sleep(delay)
        time.sleep(_ORCHESTRA_SECONDS_PER_REQUEST)
        return self.client.request(method, path, **kwargs)

    def existing_assets(self, integration_account_id: str) -> dict[str, dict]:
        assets: dict[str, dict] = {}
        page = 1
        while True:
            response = self.request(
                "GET",
                "/assets",
                params={
                    "integration": "DATABRICKS",
                    "integration_account_id": integration_account_id,
                    "page": page,
                    "page_size": 100,
                },
            )
            response.raise_for_status()
            payload = response.json()
            results = payload.get("results") or []
            for asset in results:
                assets[asset["externalId"]] = asset
            if not results or page * payload["pageSize"] >= payload["total"]:
                return assets
            page += 1


def asset_body(row: dict, integration_account_id: str) -> dict:
    body = {
        "externalId": ".".join(
            (
                integration_account_id,
                row["table_catalog"],
                row["table_schema"],
                row["table_name"],
            )
        ),
        "assetName": row["table_name"],
        "integration": "DATABRICKS",
        "integrationAccountId": integration_account_id,
        "assetType": "VIEW" if row["table_type"] == "VIEW" else "TABLE",
        "integrationAssetType": row["table_type"],
        "databaseName": row["table_catalog"],
        "schemaName": row["table_schema"],
        "tableName": row["table_name"],
        "description": row["comment"],
        "owners": [row["table_owner"]] if row["table_owner"] else None,
        "createdInIntegration": row["created"],
        "lastUpdatedInIntegration": row["last_altered"],
    }
    return {key: value for key, value in body.items() if value is not None}


def _as_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def is_unchanged(body: dict, existing: dict) -> bool:
    return all(
        _as_utc(body.get(field)) == _as_utc(existing.get(field))
        if field in _TIMESTAMP_FIELDS
        else body.get(field) == existing.get(field)
        for field in _COMPARED_FIELDS
    )


def publish_assets(
    orchestra: Orchestra | None, bodies: list[dict], existing: dict
) -> set[str]:
    """Returns the externalIds that failed to publish."""
    created = updated = skipped = 0
    failed: set[str] = set()
    for index, body in enumerate(bodies, start=1):
        external_id = body["externalId"]
        current = existing.get(external_id)

        if current and is_unchanged(body, current):
            skipped += 1
        elif orchestra is None:
            logger.info("Would %s %s", "update" if current else "create", external_id)
            if current:
                updated += 1
            else:
                created += 1
        else:
            if current:
                patch = {key: body.get(key) for key in _COMPARED_FIELDS}
                response = orchestra.request(
                    "PATCH", f"/assets/{external_id}", json=patch
                )
            else:
                response = orchestra.request("POST", "/assets", json=body)

            # A 409 means a retried POST already landed, or the asset was created concurrently.
            if response.is_success or response.status_code == 409:
                if current:
                    updated += 1
                else:
                    created += 1
            else:
                failed.add(external_id)
                logger.error(
                    "Failed to publish %s: %s %s",
                    external_id,
                    response.status_code,
                    response.text[:300],
                )

        if index % _PROGRESS_EVERY == 0:
            logger.info(
                "%s/%s assets processed (created=%s updated=%s skipped=%s failed=%s)",
                index,
                len(bodies),
                created,
                updated,
                skipped,
                len(failed),
            )

    logger.info(
        "Assets done: created=%s updated=%s skipped=%s failed=%s",
        created,
        updated,
        skipped,
        len(failed),
    )
    return failed


def fetch_edges(
    databricks: Databricks,
    integration_account_id: str,
    published: set[str],
    lookback_days: int,
) -> list[dict]:
    try:
        rows = databricks.query(
            _LINEAGE_SQL,
            [{"name": "lookback_days", "value": str(lookback_days), "type": "INT"}],
        )
    except (httpx.HTTPStatusError, RuntimeError) as exc:
        # Many workspaces don't grant SELECT on system.access; assets are still worth publishing.
        logger.warning(
            "Skipping lineage, could not read system.access.table_lineage: %s", exc
        )
        return []

    edges = []
    for row in rows:
        from_id = f"{integration_account_id}.{row['source_table_full_name']}"
        to_id = f"{integration_account_id}.{row['target_table_full_name']}"
        # Orchestra rejects a whole batch if one edge names an unknown asset.
        if from_id != to_id and from_id in published and to_id in published:
            edges.append(
                {
                    "fromId": from_id,
                    "toId": to_id,
                    "integration": "DATABRICKS",
                    "lineageDetail": "Databricks Unity Catalog table lineage",
                }
            )
    return edges


def publish_edges(orchestra: Orchestra | None, edges: list[dict]) -> int:
    if orchestra is None:
        for edge in edges:
            logger.info("Would link %s -> %s", edge["fromId"], edge["toId"])
        return 0

    created = failed = 0
    for start in range(0, len(edges), _EDGE_BATCH_SIZE):
        batch = edges[start : start + _EDGE_BATCH_SIZE]
        response = orchestra.request(
            "POST", "/assets/dependencies", json={"dependencies": batch}
        )
        if response.is_success:
            created += response.json().get("created", len(batch))
        else:
            failed += len(batch)
            logger.error(
                "Failed to publish lineage batch: %s %s",
                response.status_code,
                response.text[:300],
            )
    logger.info("Lineage done: created=%s failed=%s", created, failed)
    return failed


def _csv(value: str | None) -> list[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--host",
        default=os.environ.get("DATABRICKS_HOST"),
        help="Workspace host, e.g. dbc-1234.cloud.databricks.com (env DATABRICKS_HOST)",
    )
    parser.add_argument(
        "--warehouse-id",
        default=os.environ.get("DATABRICKS_WAREHOUSE_ID"),
        help="SQL warehouse to run the metadata queries on (env DATABRICKS_WAREHOUSE_ID)",
    )
    parser.add_argument(
        "--catalog",
        default=os.environ.get("DATABRICKS_CATALOGS"),
        help="Comma-separated catalogs to collect; all catalogs if unset (env DATABRICKS_CATALOGS)",
    )
    parser.add_argument(
        "--asset-types",
        default=os.environ.get("DATABRICKS_ASSET_TYPES", "TABLE,VIEW"),
        help="Comma-separated asset types to collect: TABLE, VIEW (env DATABRICKS_ASSET_TYPES)",
    )
    parser.add_argument(
        "--lineage-days",
        type=int,
        default=int(os.environ.get("DATABRICKS_LINEAGE_DAYS", "30")),
        help="Days of table lineage to publish; 0 disables lineage (env DATABRICKS_LINEAGE_DAYS)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log what would be created or updated without writing to Orchestra",
    )
    args = parser.parse_args(argv)

    args.token = os.environ.get("DATABRICKS_TOKEN")
    args.api_key = os.environ.get("ORCHESTRA_API_KEY")
    missing = [
        name
        for name, value in (
            ("--host / DATABRICKS_HOST", args.host),
            ("--warehouse-id / DATABRICKS_WAREHOUSE_ID", args.warehouse_id),
            ("DATABRICKS_TOKEN", args.token),
            ("ORCHESTRA_API_KEY", args.api_key),
        )
        if not value
    ]
    if missing:
        parser.error(f"missing required settings: {', '.join(missing)}")

    args.host = args.host.removeprefix("https://").rstrip("/")
    args.catalogs = set(_csv(args.catalog))
    args.asset_types = {asset_type.upper() for asset_type in _csv(args.asset_types)}
    unknown = args.asset_types - {"TABLE", "VIEW"}
    if unknown:
        parser.error(f"unsupported asset types: {', '.join(sorted(unknown))}")
    return args


def main(argv: list[str]) -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    args = parse_args(argv)
    # Matches the built-in collector's integrationAccountId and externalId prefix.
    integration_account_id = args.host.split(".")[0]

    databricks = Databricks(args.host, args.token, args.warehouse_id)
    orchestra = Orchestra(args.api_key)

    rows = databricks.query(_TABLES_SQL)
    bodies = [
        body
        for body in (asset_body(row, integration_account_id) for row in rows)
        if body["assetType"] in args.asset_types
        and (not args.catalogs or body["databaseName"] in args.catalogs)
    ]
    logger.info(
        "Found %s Databricks assets (%s before filters)", len(bodies), len(rows)
    )

    existing = orchestra.existing_assets(integration_account_id)
    logger.info(
        "Orchestra already has %s assets for %s", len(existing), integration_account_id
    )

    writer = None if args.dry_run else orchestra
    failed_ids = publish_assets(writer, bodies, existing)
    failures = len(failed_ids)

    if args.lineage_days > 0:
        published = {body["externalId"] for body in bodies} - failed_ids
        edges = fetch_edges(
            databricks, integration_account_id, published, args.lineage_days
        )
        logger.info("Found %s lineage edges between published assets", len(edges))
        failures += publish_edges(writer, edges)

    if failures:
        logger.error("%s writes failed, see the errors above", failures)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
