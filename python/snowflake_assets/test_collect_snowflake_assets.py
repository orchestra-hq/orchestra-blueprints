"""Offline check of the publish logic: python test_collect_snowflake_assets.py"""

import json
from datetime import UTC, datetime

import httpx
from collect_snowflake_assets import (
    OrchestraClient,
    fetch_lineage,
    fetch_tables,
    list_existing_assets,
    publish_assets,
    publish_edges,
)

ACCOUNT = "ACME"
CREATED = datetime(2026, 1, 1, tzinfo=UTC)


class FakeCursor:
    def __init__(self, results):
        self._results = iter(results)

    def execute(self, sql, params=None):
        self._rows = next(self._results)

    def fetchall(self):
        return self._rows


def test_publish():
    cursor = FakeCursor(
        [
            [
                ("DB", "S", "NEW", "me", "BASE TABLE", CREATED, CREATED, None),
                ("DB", "S", "SAME", "me", "VIEW", CREATED, CREATED, "doc"),
                ("DB", "S", "CHANGED", "me", "BASE TABLE", CREATED, CREATED, "new doc"),
            ],
            [],
            [("DB", "S", "NEW", "DB", "S", "SAME", "proc")],
            [("DB", "S", "CHANGED", "DB", "S", "GONE", None)],
        ]
    )
    assets = fetch_tables(cursor, ACCOUNT, "DB", {"TABLE", "VIEW"})
    edges = fetch_lineage(cursor, ACCOUNT, assets)
    assert [a["assetType"] for a in assets] == ["TABLE", "VIEW", "TABLE"]
    assert (
        edges[0]["fromId"] == "ACME.DB.S.NEW" and edges[0]["toId"] == "ACME.DB.S.SAME"
    )
    assert (
        edges[1]["fromId"] == "ACME.DB.S.GONE"
        and edges[1]["toId"] == "ACME.DB.S.CHANGED"
    )

    def existing(name, description):
        return {
            "assetId": name,
            "externalId": f"ACME.DB.S.{name}",
            "databaseName": "DB",
            "schemaName": "S",
            "tableName": name,
            "description": description,
            "owners": ["me"],
            "createdInIntegration": "2026-01-01T00:00:00Z",
            "lastUpdatedInIntegration": "2026-01-01T00:00:00Z",
        }

    calls = []
    rate_limited = {"done": False}

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.method == "GET":
            results = [existing("SAME", "doc"), existing("CHANGED", "old doc")]
            return httpx.Response(200, json={"results": results, "total": 2})
        if request.method == "POST" and not rate_limited["done"]:
            rate_limited["done"] = True
            return httpx.Response(429, headers={"Retry-After": "0"})
        if request.url.path.endswith("/dependencies"):
            return httpx.Response(
                201, json={"created": len(json.loads(request.content)["dependencies"])}
            )
        if request.method == "PATCH":
            assert json.loads(request.content) == {"description": "new doc"}
        return httpx.Response(200 if request.method == "PATCH" else 201, json={})

    client = OrchestraClient("key", "https://test", 0, httpx.MockTransport(handler))
    current = list_existing_assets(client, ACCOUNT)
    counts, failed_ids = publish_assets(client, assets, current)
    assert counts == {"created": 1, "updated": 1, "skipped": 1, "failed": 0}, counts

    assert failed_ids == set()
    known = set(current) | {a["externalId"] for a in assets}
    edge_counts = publish_edges(client, edges, known)
    assert edge_counts == {"created": 1, "skipped": 1, "failed": 0}, edge_counts
    assert calls.count(("POST", "/assets")) == 2  # one 429, one retry


if __name__ == "__main__":
    test_publish()
    print("ok")
