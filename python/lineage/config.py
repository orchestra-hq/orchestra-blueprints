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

# BigQuery landing zone for the raw metadata dlt extracts. publish_lineage.py
# queries this directly (see queries.py) -- there is no separate mart dataset.
RAW_DATASET = os.environ.get("LINEAGE_RAW_DATASET", "platform_lineage_raw")

# GCP project that owns the dataset above, and the location it lives in.
BQ_PROJECT = os.environ.get("BIGQUERY_PROJECT") or os.environ.get(
    "LINEAGE_BQ_PROJECT", ""
)
BQ_LOCATION = os.environ.get("BIGQUERY_LOCATION", "europe-west1")


class MissingCredentials(RuntimeError):
    """Raised when a source is asked to run without the secrets it needs."""


# Statuses that mean "this one object is not available to us" rather than "the
# credential is wrong". Skipping these keeps one inaccessible object from
# emptying the whole graph, while 401s and 5xxs still fail the load -- silently
# publishing an empty lineage graph is worse than failing.
SKIPPABLE_STATUSES = (403, 404)


def is_skippable(error: Exception) -> bool:
    """True when an HTTP error refers to one missing/forbidden object."""
    response = getattr(error, "response", None)
    return getattr(response, "status_code", None) in SKIPPABLE_STATUSES


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
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as fh:
        json.dump(parsed, fh)
        creds_path = fh.name
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path

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
