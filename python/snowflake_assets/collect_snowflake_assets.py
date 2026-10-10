"""Collect Snowflake tables and views into Orchestra through the public asset API.

Replaces Orchestra's scheduled Snowflake asset runs; see README.md for setup.
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime
from typing import Any

import httpx
import snowflake.connector

logger = logging.getLogger("collect_snowflake_assets")

API_BASE = os.environ.get(
    "ORCHESTRA_API_BASE", "https://app.getorchestra.io/api/engine/public"
).rstrip("/")

# Under the metadata API's 50/minute limit, leaving headroom for other jobs on the same key.
PACING_SECONDS = 60 / 50 * 1.25
MAX_RETRIES = 5
PAGE_SIZE = 100
EDGE_BATCH_SIZE = 100
ASSET_TYPES = ("TABLE", "VIEW")
LINEAGE_UNAVAILABLE = "Unsupported feature 'Data Lineage'"


class OrchestraClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = API_BASE,
        pacing_seconds: float = PACING_SECONDS,
        transport: httpx.BaseTransport | None = None,
    ):
        self._http = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=120,
            transport=transport,
        )
        self._pacing_seconds = pacing_seconds
        self._last_request_at = 0.0

    def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        for attempt in range(MAX_RETRIES + 1):
            wait = self._last_request_at + self._pacing_seconds - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self._last_request_at = time.monotonic()

            response = self._http.request(method, path, **kwargs)
            if response.status_code != 429 or attempt == MAX_RETRIES:
                return response

            delay = _retry_after(response)
            if delay is None:
                delay = 2 ** (attempt + 1)
            logger.warning(
                "Rate limited on %s %s; retrying in %ss", method, path, delay
            )
            time.sleep(delay)
        raise AssertionError("unreachable")


def _retry_after(response: httpx.Response) -> float | None:
    try:
        return float(response.headers["Retry-After"])
    except (KeyError, ValueError):
        return None


def connect_to_snowflake(
    warehouse: str | None,
) -> snowflake.connector.SnowflakeConnection:
    params: dict[str, Any] = {
        "account": _require_env("SNOWFLAKE_ACCOUNT"),
        "user": _require_env("SNOWFLAKE_USER"),
        "role": os.environ.get("SNOWFLAKE_ROLE"),
        "warehouse": warehouse,
    }
    if os.environ.get("SNOWFLAKE_PRIVATE_KEY"):
        params["private_key"] = _private_key_der(
            os.environ["SNOWFLAKE_PRIVATE_KEY"],
            os.environ.get("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE"),
        )
    else:
        params["password"] = _require_env("SNOWFLAKE_PASSWORD")
    return snowflake.connector.connect(**{k: v for k, v in params.items() if v})


def _private_key_der(pem: str, passphrase: str | None) -> bytes:
    # cryptography is installed with snowflake-connector-python.
    from cryptography.hazmat.primitives import serialization

    key = serialization.load_pem_private_key(
        pem.encode(), password=passphrase.encode() if passphrase else None
    )
    return key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        sys.exit(f"Missing required environment variable {name}; see README.md")
    return value


def asset_type_for(table_type: str) -> str:
    return "VIEW" if table_type == "VIEW" else "TABLE"


def fetch_tables(
    cursor: Any, account: str, database: str, asset_types: set[str]
) -> list[dict[str, Any]]:
    cursor.execute(
        "SELECT TABLE_CATALOG, TABLE_SCHEMA, TABLE_NAME, TABLE_OWNER,"
        " TABLE_TYPE, CREATED, LAST_DDL, COMMENT"
        f" FROM {database}.information_schema.tables"
        " WHERE table_schema != 'INFORMATION_SCHEMA';"
    )
    tables = []
    for (
        db,
        schema,
        name,
        owner,
        table_type,
        created,
        last_ddl,
        comment,
    ) in cursor.fetchall():
        if asset_type_for(table_type) not in asset_types:
            continue
        tables.append(
            {
                "assetName": name,
                "externalId": f"{account}.{db}.{schema}.{name}",
                "integration": "SNOWFLAKE",
                "integrationAccountId": account,
                "assetType": asset_type_for(table_type),
                "integrationAssetType": table_type,
                "databaseName": db,
                "schemaName": schema,
                "tableName": name,
                "description": comment,
                "owners": [owner] if owner else None,
                "createdInIntegration": _iso(created),
                "lastUpdatedInIntegration": _iso(last_ddl),
            }
        )
    logger.info("Found %d assets in %s", len(tables), database)
    return tables


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def fetch_lineage(
    cursor: Any, account: str, tables: list[dict[str, Any]]
) -> list[dict[str, str]]:
    """Upstream edges for each table, from SNOWFLAKE.CORE.GET_LINEAGE."""
    edges = []
    for table in tables:
        name = ".".join(
            '"{}"'.format(table[part].replace('"', '""'))
            for part in ("databaseName", "schemaName", "tableName")
        )
        try:
            # Snowflake doesn't document which end of an UPSTREAM row is the queried object.
            cursor.execute(
                "SELECT DISTINCT SOURCE_OBJECT_DATABASE, SOURCE_OBJECT_SCHEMA,"
                " SOURCE_OBJECT_NAME, TARGET_OBJECT_DATABASE, TARGET_OBJECT_SCHEMA,"
                " TARGET_OBJECT_NAME, PROCESS FROM TABLE"
                " (SNOWFLAKE.CORE.GET_LINEAGE(%s, 'TABLE', 'UPSTREAM', 1));",
                (name,),
            )
        except snowflake.connector.errors.ProgrammingError as error:
            if LINEAGE_UNAVAILABLE in str(error):
                logger.warning(
                    "GET_LINEAGE needs Snowflake Enterprise Edition; skipping lineage"
                )
                return []
            logger.warning("Failed to fetch lineage for %s: %s", name, error)
            continue
        for *ends, process in cursor.fetchall():
            source_id = "{}.{}.{}.{}".format(account, *ends[:3])
            target_id = "{}.{}.{}.{}".format(account, *ends[3:])
            upstream_id = target_id if source_id == table["externalId"] else source_id
            edges.append(
                {
                    "fromId": upstream_id,
                    "toId": table["externalId"],
                    "lineageDetail": process or "Snowflake GET_LINEAGE",
                    "integration": "SNOWFLAKE",
                }
            )
    logger.info("Found %d lineage edges", len(edges))
    return edges


def list_existing_assets(
    client: OrchestraClient, account: str
) -> dict[str, dict[str, Any]]:
    existing: dict[str, dict[str, Any]] = {}
    page = 1
    while True:
        response = client.request(
            "GET",
            "/assets",
            params={
                "integration": "SNOWFLAKE",
                "integration_account_id": account,
                "page": page,
                "page_size": PAGE_SIZE,
            },
        )
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results") or []
        for asset in results:
            existing[asset["externalId"]] = asset
        if not results or len(existing) >= payload.get("total", 0):
            return existing
        page += 1


# The fields PATCH accepts that the collector sets.
PATCHABLE_FIELDS = (
    "databaseName",
    "schemaName",
    "tableName",
    "description",
    "owners",
    "createdInIntegration",
    "lastUpdatedInIntegration",
)


def _changed_fields(asset: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    return {
        field: asset[field]
        for field in PATCHABLE_FIELDS
        if asset[field] is not None and not _same(asset[field], current.get(field))
    }


def _same(new: Any, old: Any) -> bool:
    # Timestamps come back from the API in a different ISO format from the one sent.
    if isinstance(new, str) and isinstance(old, str):
        try:
            return datetime.fromisoformat(new) == datetime.fromisoformat(old)
        except ValueError:
            pass
    return new == old


def publish_assets(
    client: OrchestraClient,
    assets: list[dict[str, Any]],
    existing: dict[str, dict[str, Any]],
) -> tuple[dict[str, int], set[str]]:
    """Returns the outcome counts and the externalIds that failed to publish."""
    counts = {"created": 0, "updated": 0, "skipped": 0, "failed": 0}
    failed_ids = set()
    for index, asset in enumerate(assets, start=1):
        current = existing.get(asset["externalId"])
        if current is None:
            body = {k: v for k, v in asset.items() if v is not None}
            response = client.request("POST", "/assets", json=body)
            outcome = "created"
        else:
            changes = _changed_fields(asset, current)
            if not changes:
                counts["skipped"] += 1
                continue
            response = client.request(
                "PATCH", f"/assets/{current['assetId']}", json=changes
            )
            outcome = "updated"

        if response.is_success:
            counts[outcome] += 1
        else:
            counts["failed"] += 1
            failed_ids.add(asset["externalId"])
            logger.error(
                "Failed to publish %s: %s %s",
                asset["externalId"],
                response.status_code,
                response.text[:300],
            )
        if index % 25 == 0:
            logger.info("Processed %d/%d assets: %s", index, len(assets), counts)
    return counts, failed_ids


def publish_edges(
    client: OrchestraClient, edges: list[dict[str, str]], known_ids: set[str]
) -> dict[str, int]:
    # The API rejects a whole batch if either end of any edge isn't an asset yet.
    unique = {
        (edge["fromId"], edge["toId"]): edge
        for edge in edges
        if {edge["fromId"], edge["toId"]} <= known_ids
        and edge["fromId"] != edge["toId"]
    }
    batch_edges = list(unique.values())
    counts = {"created": 0, "skipped": len(edges) - len(batch_edges), "failed": 0}
    for start in range(0, len(batch_edges), EDGE_BATCH_SIZE):
        batch = batch_edges[start : start + EDGE_BATCH_SIZE]
        response = client.request(
            "POST", "/assets/dependencies", json={"dependencies": batch}
        )
        if response.is_success:
            counts["created"] += response.json().get("created", len(batch))
        else:
            counts["failed"] += len(batch)
            logger.error(
                "Failed to publish lineage batch: %s %s",
                response.status_code,
                response.text[:300],
            )
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--database", required=True, help="Snowflake database to collect"
    )
    parser.add_argument(
        "--warehouse",
        default=os.environ.get("SNOWFLAKE_WAREHOUSE"),
        help="Warehouse to run the metadata queries on (default: $SNOWFLAKE_WAREHOUSE)",
    )
    parser.add_argument(
        "--asset-types",
        default=",".join(ASSET_TYPES),
        help="Comma-separated asset types to collect: TABLE, VIEW (default: both)",
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )

    asset_types = {value.strip().upper() for value in args.asset_types.split(",")}
    if unknown := asset_types - set(ASSET_TYPES):
        parser.error(f"unknown asset types: {', '.join(sorted(unknown))}")

    client = OrchestraClient(_require_env("ORCHESTRA_API_KEY"))
    account = _require_env("SNOWFLAKE_ACCOUNT").upper()

    with (
        connect_to_snowflake(args.warehouse) as connection,
        connection.cursor() as cursor,
    ):
        assets = fetch_tables(cursor, account, args.database, asset_types)
        edges = fetch_lineage(cursor, account, assets)

    existing = list_existing_assets(client, account)
    logger.info("Orchestra already has %d assets for %s", len(existing), account)

    asset_counts, failed_ids = publish_assets(client, assets, existing)
    logger.info("Assets: %s", asset_counts)

    known_ids = (set(existing) | {asset["externalId"] for asset in assets}) - failed_ids
    edge_counts = publish_edges(client, edges, known_ids)
    logger.info("Lineage edges: %s", edge_counts)

    return 1 if asset_counts["failed"] or edge_counts["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
