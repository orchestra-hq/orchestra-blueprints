"""Shared configuration for the platform-lineage dlt sources.

Every value comes from an environment variable so the same code runs locally and
inside an Orchestra Python task (Orchestra injects connection secrets as env
vars). Nothing is hardcoded and nothing is read from a `secrets.toml`.
"""

import json
import os
import tempfile

# The three metadata sources dlt currently extracts. Adding a platform means
# adding its name here plus a module in `sources/` -- see README.
KNOWN_SOURCES = ("lightdash", "bigquery", "fivetran")

# BigQuery landing zone for the raw metadata dlt extracts.
RAW_DATASET = os.environ.get("LINEAGE_RAW_DATASET", "platform_lineage_raw")

# BigQuery dataset holding the dbt-built `lineage_assets` / `lineage_edges` marts.
MART_DATASET = os.environ.get("LINEAGE_MART_DATASET", "platform_lineage")

# GCP project that owns both datasets, and the location they live in.
BQ_PROJECT = os.environ.get("BIGQUERY_PROJECT") or os.environ.get(
    "LINEAGE_BQ_PROJECT", ""
)
BQ_LOCATION = os.environ.get("BIGQUERY_LOCATION", "europe-west1")


class MissingCredentials(RuntimeError):
    """Raised when a source is asked to run without the secrets it needs."""


def require_env(*names: str) -> list[str]:
    """Return the values of `names`, or raise listing every one that is unset."""
    missing = [name for name in names if not os.environ.get(name)]
    if missing:
        raise MissingCredentials(
            "missing required environment variable(s): "
            + ", ".join(missing)
            + " -- add them to the Orchestra connection's secret JSON"
        )
    return [os.environ[name] for name in names]


def ensure_google_credentials() -> None:
    """Bridge `BIGQUERY_CREDENTIALS_JSON` to a file for the Google SDKs.

    The existing Orchestra connections store the service account as a raw JSON
    string (that is what `target-bigquery` in `python/meltano` expects), but the
    Google client libraries and dlt's BigQuery destination both want either
    `GOOGLE_APPLICATION_CREDENTIALS` pointing at a file or the
    `DESTINATION__BIGQUERY__CREDENTIALS__*` triple. Writing the string out to a
    temp file lets one connection serve both.
    """
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        return

    raw = os.environ.get("BIGQUERY_CREDENTIALS_JSON")
    if not raw:
        return

    parsed = json.loads(raw)
    handle = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    with handle as fh:
        json.dump(parsed, fh)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = handle.name

    # dlt reads its BigQuery destination credentials from these three vars.
    os.environ.setdefault(
        "DESTINATION__BIGQUERY__CREDENTIALS__PROJECT_ID", parsed["project_id"]
    )
    os.environ.setdefault(
        "DESTINATION__BIGQUERY__CREDENTIALS__PRIVATE_KEY", parsed["private_key"]
    )
    os.environ.setdefault(
        "DESTINATION__BIGQUERY__CREDENTIALS__CLIENT_EMAIL", parsed["client_email"]
    )


def resolved_bq_project() -> str:
    """The GCP project to read metadata from and land dlt output into."""
    ensure_google_credentials()
    if BQ_PROJECT:
        return BQ_PROJECT

    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path and os.path.exists(creds_path):
        with open(creds_path, encoding="utf-8") as fh:
            project = json.load(fh).get("project_id")
        if project:
            return project

    raise MissingCredentials(
        "cannot determine the BigQuery project -- set BIGQUERY_PROJECT"
    )
