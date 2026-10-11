from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from google.cloud.bigquery.job import QueryJob
from orchestra_sdk.errors import LinkedConnectionNotFoundError

from collect_bigquery_assets import (
    api_base,
    asset_body,
    changed_fields,
    job_tables,
    script_statements,
    service_account_info,
)

CREATED = datetime(2026, 1, 1, tzinfo=UTC)


def table(**overrides):
    fields = {
        "project": "proj",
        "dataset_id": "ds",
        "table_id": "orders",
        "friendly_name": None,
        "table_type": "TABLE",
        "created": CREATED,
        "modified": None,
    }
    return SimpleNamespace(**{**fields, **overrides})


class Ref:
    def __init__(self, name):
        self.name = name
        self.table_id = name.split(".")[-1]

    def __str__(self):
        return self.name


def test_asset_body_matches_built_in_collector():
    body = asset_body(table(table_type="VIEW"))
    assert body == {
        "externalId": "proj.ds.orders",
        "assetName": "orders",
        "integration": "GCP_BIG_QUERY",
        "integrationAccountId": "proj",
        "assetType": "VIEW",
        "integrationAssetType": "VIEW",
        "databaseName": "ds",
        "tableName": "orders",
        "createdInIntegration": CREATED.isoformat(),
    }


def test_job_tables_ignores_anonymous_destinations():
    job = SimpleNamespace(
        referenced_tables=[Ref("proj.ds.raw")],
        destination=Ref("proj._abc.anon" + "0" * 64),
        ddl_target_table=Ref("proj.ds.orders"),
    )
    assert job_tables(job) == ({"proj.ds.raw"}, {"proj.ds.orders"})


def test_changed_fields_compares_datetimes_not_strings():
    body = asset_body(table())
    existing = {
        "databaseName": "ds",
        "tableName": "orders",
        "createdInIntegration": "2026-01-01T00:00:00Z",
    }
    assert changed_fields(body, existing) == {}
    assert changed_fields(body, {**existing, "databaseName": "old"}) == {
        "databaseName": "ds"
    }


def test_script_statements_lists_each_script_once():
    child = QueryJob.__new__(QueryJob)
    calls = []

    def list_jobs(**kwargs):
        calls.append(kwargs["parent_job"])
        return [child, SimpleNamespace()]

    client = SimpleNamespace(list_jobs=list_jobs)
    seen: set[str] = set()
    first = SimpleNamespace(query="BEGIN MERGE ...; END", job_id="a")
    second = SimpleNamespace(query="BEGIN MERGE ...; END", job_id="b")
    assert script_statements(client, first, seen) == [child]
    assert script_statements(client, second, seen) == []
    assert calls == [first]


def test_service_account_info_uses_the_linked_connection(monkeypatch):
    for name in ("BIGQUERY_CREDENTIALS_JSON", "BIGQUERY_CONNECTION_ID"):
        monkeypatch.delenv(name, raising=False)
    assert service_account_info() is None

    monkeypatch.setenv(
        "GCP_BIG_QUERY__PROD_12345__SERVICE_ACCOUNT_JSON", '{"project_id": "prod"}'
    )
    assert service_account_info() == {"project_id": "prod"}

    monkeypatch.setenv(
        "GCP_BIG_QUERY__DEV_54321__SERVICE_ACCOUNT_JSON", '{"project_id": "dev"}'
    )
    with pytest.raises(LinkedConnectionNotFoundError):
        service_account_info()
    monkeypatch.setenv("BIGQUERY_CONNECTION_ID", "dev_54321")
    assert service_account_info() == {"project_id": "dev"}

    monkeypatch.setenv("BIGQUERY_CREDENTIALS_JSON", '{"project_id": "explicit"}')
    assert service_account_info() == {"project_id": "explicit"}


def test_api_base_accepts_a_bare_host(monkeypatch):
    monkeypatch.delenv("ORCHESTRA_BASE_URL", raising=False)
    assert api_base() == "https://app.getorchestra.io/api/engine/public"
    monkeypatch.setenv("ORCHESTRA_BASE_URL", "stage.getorchestra.io")
    assert api_base() == "https://stage.getorchestra.io/api/engine/public"
    monkeypatch.setenv("ORCHESTRA_BASE_URL", "http://localhost:8000/")
    assert api_base() == "http://localhost:8000/api/engine/public"
