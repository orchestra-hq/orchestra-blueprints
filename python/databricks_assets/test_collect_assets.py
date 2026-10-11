from orchestra_sdk.linked_connections import get_linked_connection

import collect_assets
from collect_assets import api_base, asset_body, databricks_token, is_unchanged

ROW = {
    "table_catalog": "main",
    "table_schema": "sales",
    "table_name": "orders",
    "table_type": "MANAGED",
    "table_owner": "ana@example.com",
    "comment": None,
    "created": "2026-01-01T00:00:00.000Z",
    "last_altered": "2026-01-02T00:00:00.000Z",
}


def test_asset_body_matches_built_in_collector():
    assert asset_body(ROW, "dbc-1234") == {
        "externalId": "dbc-1234.main.sales.orders",
        "assetName": "orders",
        "integration": "DATABRICKS",
        "integrationAccountId": "dbc-1234",
        "assetType": "TABLE",
        "integrationAssetType": "MANAGED",
        "databaseName": "main",
        "schemaName": "sales",
        "tableName": "orders",
        "owners": ["ana@example.com"],
        "createdInIntegration": "2026-01-01T00:00:00.000Z",
        "lastUpdatedInIntegration": "2026-01-02T00:00:00.000Z",
    }


def test_views_are_view_assets():
    assert asset_body({**ROW, "table_type": "VIEW"}, "dbc-1234")["assetType"] == "VIEW"


def test_unchanged_across_timestamp_formats():
    body = asset_body(ROW, "dbc-1234")
    existing = {
        **body,
        "createdInIntegration": "2026-01-01T00:00:00",
        "lastUpdatedInIntegration": "2026-01-02T00:00:00+00:00",
    }
    assert is_unchanged(body, existing)
    assert not is_unchanged(
        body, {**existing, "lastUpdatedInIntegration": "2026-01-03T00:00:00"}
    )


def test_api_base_accepts_bare_host(monkeypatch):
    monkeypatch.setenv("ORCHESTRA_BASE_URL", "stage.getorchestra.io")
    assert api_base() == "https://stage.getorchestra.io/api/engine/public"
    monkeypatch.delenv("ORCHESTRA_BASE_URL")
    assert api_base() == "https://app.getorchestra.io/api/engine/public"


PREFIX = "DATABRICKS__DEMO_39533__"


def link(monkeypatch, **fields):
    for name, value in fields.items():
        monkeypatch.setenv(PREFIX + name.upper(), value)
    return get_linked_connection("DATABRICKS")


def test_pat_connection_uses_its_access_token(monkeypatch):
    connection = link(
        monkeypatch, databricks_auth_type="PAT", databricks_access_token="pat\n"
    )
    assert databricks_token(connection, "dbc-1234") == "pat"


def test_oauth_connection_ignores_stale_access_token(monkeypatch):
    connection = link(
        monkeypatch,
        databricks_auth_type="OAUTH",
        databricks_access_token="stale",
        databricks_client_id="cid",
        databricks_client_secret="secret",
    )
    monkeypatch.setattr(
        collect_assets,
        "oauth_token",
        lambda host, cid, secret: f"{host}:{cid}:{secret}",
    )
    assert databricks_token(connection, "dbc-1234") == "dbc-1234:cid:secret"
