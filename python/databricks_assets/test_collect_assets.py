import pytest

from collect_assets import api_base, asset_body, is_unchanged, linked_connection

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


def test_linked_connection_reads_single_connection(monkeypatch):
    monkeypatch.setenv("DATABRICKS__PROD_1__DATABRICKS_WORKSPACE_HOST", "dbc-1234")
    monkeypatch.setenv("DATABRICKS__PROD_1__DATABRICKS_ACCESS_TOKEN", "pat")
    assert linked_connection() == {
        "databricks_workspace_host": "dbc-1234",
        "databricks_access_token": "pat",
    }


def test_linked_connection_refuses_to_guess(monkeypatch):
    monkeypatch.setenv("DATABRICKS__PROD_1__DATABRICKS_WORKSPACE_HOST", "dbc-1")
    monkeypatch.setenv("DATABRICKS__DEV_2__DATABRICKS_WORKSPACE_HOST", "dbc-2")
    with pytest.raises(SystemExit, match="several Databricks connections"):
        linked_connection()
