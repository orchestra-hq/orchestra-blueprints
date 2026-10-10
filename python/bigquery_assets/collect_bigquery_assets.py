"""Write BigQuery tables, views and job-history lineage to Orchestra via the public asset API.

See README.md for setup, auth and scheduling."""

import json
import logging
import os
import re
import sys
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from google.api_core.exceptions import GoogleAPICallError
from google.cloud import bigquery
from google.cloud.bigquery.job import QueryJob
from google.oauth2 import service_account

logger = logging.getLogger("collect_bigquery_assets")

API_BASE = os.environ.get(
    "ORCHESTRA_API_BASE", "https://app.getorchestra.io/api/engine/public"
).rstrip("/")
INTEGRATION = "GCP_BIG_QUERY"
SUPPORTED_ASSET_TYPES = {"TABLE", "VIEW"}
JOB_LOOKBACK = timedelta(days=7)
LINEAGE_DETAIL = "Derived from BigQuery job history"

# 80% of the metadata API's 50/minute limit, leaving room for other users of the key.
REQUEST_INTERVAL_SECONDS = 60 / 40
MAX_RETRIES = 6
TIMEOUT_SECONDS = 60
EDGE_BATCH_SIZE = 100
PROGRESS_EVERY = 25

# BigQuery names temporary query results `anon` followed by 64 hex characters.
ANONYMOUS_TABLE = re.compile(r"^anon[0-9a-f]{64}$")
PATCHABLE_FIELDS = (
    "databaseName",
    "tableName",
    "createdInIntegration",
    "lastUpdatedInIntegration",
)


def load_config() -> tuple[str, bigquery.Client, str, set[str]]:
    api_key = os.environ.get("ORCHESTRA_API_KEY", "")

    raw_credentials = os.environ.get("BIGQUERY_CREDENTIALS_JSON")
    if raw_credentials:
        info = json.loads(raw_credentials)
        credentials = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/bigquery"]
        )
        default_project = info["project_id"]
    else:
        # Falls back to GOOGLE_APPLICATION_CREDENTIALS or other default credentials.
        credentials = None
        default_project = None

    project = os.environ.get("BIGQUERY_PROJECT") or default_project
    client = bigquery.Client(project=project, credentials=credentials)

    asset_types = {
        value.strip().upper()
        for value in os.environ.get("ASSET_TYPES", "TABLE,VIEW").split(",")
        if value.strip()
    }
    unsupported = asset_types - SUPPORTED_ASSET_TYPES
    if unsupported:
        raise SystemExit(
            f"unsupported ASSET_TYPES {sorted(unsupported)}; choose from TABLE, VIEW"
        )
    return api_key, client, client.project, asset_types


def collect_tables(client: bigquery.Client) -> list[bigquery.Table]:
    tables = []
    datasets = [dataset.dataset_id for dataset in client.list_datasets()]
    logger.info("found %d datasets in %s", len(datasets), client.project)
    for dataset_id in datasets:
        try:
            references = [table.reference for table in client.list_tables(dataset_id)]
        except GoogleAPICallError as exc:
            logger.warning("could not list tables in %s: %s", dataset_id, exc)
            continue
        for reference in references:
            try:
                tables.append(client.get_table(reference))
            except GoogleAPICallError as exc:
                logger.warning("could not get table %s: %s", reference, exc)
    logger.info("found %d tables and views", len(tables))
    return tables


def asset_type(table: bigquery.Table) -> str:
    return "VIEW" if table.table_type == "VIEW" else "TABLE"


def asset_body(table: bigquery.Table) -> dict[str, Any]:
    external_id = f"{table.project}.{table.dataset_id}.{table.table_id}"
    body = {
        "externalId": external_id,
        "assetName": table.friendly_name or table.table_id,
        "integration": INTEGRATION,
        "integrationAccountId": table.project,
        "assetType": asset_type(table),
        "integrationAssetType": table.table_type,
        "databaseName": table.dataset_id,
        "tableName": table.table_id,
        "createdInIntegration": table.created.isoformat() if table.created else None,
        "lastUpdatedInIntegration": (
            table.modified.isoformat() if table.modified else None
        ),
    }
    return {key: value for key, value in body.items() if value is not None}


def job_tables(job: QueryJob) -> tuple[set[str], set[str]]:
    """Return the tables a query job read from and the tables it wrote to."""
    sources = {str(table) for table in job.referenced_tables or []}
    targets = set()
    for target in (job.destination, job.ddl_target_table):
        if target and not ANONYMOUS_TABLE.match(target.table_id):
            targets.add(str(target))
    return sources, targets


def script_statements(
    client: bigquery.Client, job: QueryJob, seen_scripts: set[str]
) -> list[QueryJob]:
    """Child statements of a script, or none if a script with the same SQL was read."""
    # ponytail: dynamic SQL (EXECUTE IMMEDIATE) can write different tables per run.
    if job.query in seen_scripts:
        return []
    try:
        children = list(client.list_jobs(parent_job=job, all_users=True))
    except GoogleAPICallError as exc:
        logger.warning("could not list statements of script %s: %s", job.job_id, exc)
        return []
    seen_scripts.add(job.query)
    return [child for child in children if isinstance(child, QueryJob)]


def collect_edges(client: bigquery.Client, known_ids: set[str]) -> set[tuple[str, str]]:
    """Lineage edges between known assets, from the last week of query jobs."""
    edges = set()
    seen_scripts: set[str] = set()
    try:
        jobs = client.list_jobs(
            all_users=True,
            min_creation_time=datetime.now(UTC) - JOB_LOOKBACK,
        )
        for job in jobs:
            if not isinstance(job, QueryJob) or job.error_result:
                continue
            # Scripts (e.g. dbt incremental models) read and write in child jobs.
            statements = (
                script_statements(client, job, seen_scripts)
                if job.statement_type == "SCRIPT"
                else [job]
            )
            for statement in statements:
                if statement.error_result:
                    continue
                sources, targets = job_tables(statement)
                edges.update(
                    (source, target)
                    for source in sources & known_ids
                    for target in targets & known_ids
                    if source != target
                )
    except GoogleAPICallError as exc:
        # Needs bigquery.jobs.listAll; assets are still worth writing without lineage.
        logger.warning("could not list query jobs, skipping lineage: %s", exc)
    logger.info("found %d lineage edges", len(edges))
    return edges


class OrchestraClient:
    def __init__(self, api_key: str) -> None:
        self._http = httpx.Client(
            base_url=API_BASE,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=TIMEOUT_SECONDS,
        )
        self._last_request = 0.0

    def _send(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        wait = self._last_request + REQUEST_INTERVAL_SECONDS - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self._last_request = time.monotonic()
        return self._http.request(method, path, **kwargs)

    def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        for attempt in range(MAX_RETRIES):
            try:
                response = self._send(method, path, **kwargs)
            except httpx.TransportError as exc:
                reason, retry_after = str(exc), ""
            else:
                if response.status_code != 429 and response.status_code < 500:
                    return response
                reason = f"returned {response.status_code}"
                retry_after = response.headers.get("Retry-After", "")
            backoff = (
                float(retry_after) if retry_after.isdigit() else 2 ** (attempt + 2)
            )
            logger.warning("%s %s %s, retrying in %.0fs", method, path, reason, backoff)
            time.sleep(backoff)
        return self._send(method, path, **kwargs)

    def existing_assets(self, project: str) -> dict[str, dict[str, Any]]:
        assets: dict[str, dict[str, Any]] = {}
        page = 1
        while True:
            response = self.request(
                "GET",
                "/assets",
                params={
                    "integration": INTEGRATION,
                    "integration_account_id": project,
                    "page": page,
                    "page_size": 100,
                },
            )
            response.raise_for_status()
            payload = response.json()
            results = payload.get("results") or []
            for asset in results:
                assets[asset["externalId"]] = asset
            if not results or len(assets) >= payload.get("total", 0):
                return assets
            page += 1


def _parse(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass
    return value


def changed_fields(body: dict[str, Any], existing: dict[str, Any]) -> dict[str, Any]:
    """The patchable fields in `body` that differ from the asset Orchestra has."""
    return {
        field: body[field]
        for field in PATCHABLE_FIELDS
        if field in body and _parse(body[field]) != _parse(existing.get(field))
    }


def sync_assets(
    orchestra: OrchestraClient, bodies: list[dict[str, Any]], project: str
) -> tuple[set[str], int]:
    """Create or update every asset. Returns the external IDs now in Orchestra."""
    existing = orchestra.existing_assets(project)
    logger.info("Orchestra already has %d assets for %s", len(existing), project)
    synced: set[str] = set()
    created = updated = skipped = failed = 0

    for index, body in enumerate(bodies, start=1):
        external_id = body["externalId"]
        if external_id in existing:
            patch = changed_fields(body, existing[external_id])
            if not patch:
                skipped += 1
                synced.add(external_id)
                continue
            asset_id = existing[external_id]["assetId"]
            response = orchestra.request("PATCH", f"/assets/{asset_id}", json=patch)
            updated += response.is_success
        else:
            response = orchestra.request("POST", "/assets", json=body)
            created += response.is_success

        if response.is_success:
            synced.add(external_id)
        elif response.status_code == 409:
            # Exists under another integrationAccountId, so the listing missed it.
            skipped += 1
            synced.add(external_id)
        else:
            failed += 1
            logger.error(
                "failed to write %s: %d %s",
                external_id,
                response.status_code,
                response.text[:300],
            )
        if index % PROGRESS_EVERY == 0:
            logger.info("processed %d/%d assets", index, len(bodies))

    logger.info(
        "assets: created=%d updated=%d skipped=%d failed=%d",
        created,
        updated,
        skipped,
        failed,
    )
    return synced, failed


def sync_edges(orchestra: OrchestraClient, edges: list[tuple[str, str]]) -> int:
    dependencies = [
        {
            "fromId": source,
            "toId": target,
            "lineageDetail": LINEAGE_DETAIL,
            "integration": INTEGRATION,
        }
        for source, target in edges
    ]
    created = failed = 0
    for start in range(0, len(dependencies), EDGE_BATCH_SIZE):
        batch = dependencies[start : start + EDGE_BATCH_SIZE]
        response = orchestra.request(
            "POST", "/assets/dependencies", json={"dependencies": batch}
        )
        if response.is_success:
            created += response.json().get("created", len(batch))
        else:
            failed += len(batch)
            logger.error(
                "failed to write lineage batch: %d %s",
                response.status_code,
                response.text[:300],
            )
    logger.info("lineage: written=%d failed=%d", created, failed)
    return failed


def main(dry_run: bool) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    api_key, client, project, asset_types = load_config()
    if not api_key and not dry_run:
        raise SystemExit("ORCHESTRA_API_KEY is not set")

    tables = [
        table for table in collect_tables(client) if asset_type(table) in asset_types
    ]
    bodies = [asset_body(table) for table in tables]
    edges = collect_edges(client, {body["externalId"] for body in bodies})

    if dry_run:
        for body in bodies:
            logger.info("would write %s %s", body["assetType"], body["externalId"])
        for source, target in sorted(edges):
            logger.info("would link %s -> %s", source, target)
        return 0

    orchestra = OrchestraClient(api_key)
    synced, asset_failures = sync_assets(orchestra, bodies, project)
    # One edge to a missing asset makes the endpoint reject its whole batch.
    edge_failures = sync_edges(
        orchestra,
        sorted(edge for edge in edges if edge[0] in synced and edge[1] in synced),
    )
    return 1 if asset_failures or edge_failures else 0


if __name__ == "__main__":
    sys.exit(main(dry_run="--dry-run" in sys.argv))
