"""Task 1 — declare the source catalogue and publish it via the Orchestra SDK.

Runs as an Orchestra PYTHON_EXECUTE_SCRIPT task with `set_outputs: true`.

Orchestra injects ORCHESTRA_API_KEY / ORCHESTRA_TASK_RUN_ID / ORCHESTRA_WEBHOOK_URL
automatically, so OrchestraSDK(api_key=...) is all the wiring needed. Outputs set
here are readable by any downstream task via:

    ${{ ORCHESTRA.PIPELINE_RUN_TASKS['<task-id>'].OUTPUTS['<output_name>'] }}

Output names may only contain letters and underscores (no digits, no dashes).
Values are serialised as JSON strings so they survive being injected into a
downstream task's `environment_variables` block.
"""

from __future__ import annotations

import base64
import json
import os
import sys
from datetime import datetime, timezone

from orchestra_sdk.orchestra import OrchestraSDK

# --------------------------------------------------------------------------
# The source catalogue. In real life this would come from a config file, a
# metadata table, or a call to Fivetran/Airbyte/Estuary — the shape is what
# matters, not where it comes from.
# --------------------------------------------------------------------------
SOURCES: list[dict] = [
    {
        "name": "salesforce_accounts",
        "connector": "fivetran",
        "database": "RAW",
        "schema": "SALESFORCE",
        "table": "ACCOUNTS",
        "load_strategy": "incremental",
        "cursor_field": "SYSTEMMODSTAMP",
        "freshness_sla_hours": 6,
        "enabled": True,
    },
    {
        "name": "stripe_invoices",
        "connector": "estuary",
        "database": "RAW",
        "schema": "STRIPE",
        "table": "INVOICES",
        "load_strategy": "incremental",
        "cursor_field": "UPDATED_AT",
        "freshness_sla_hours": 3,
        "enabled": True,
    },
    {
        "name": "hubspot_contacts",
        "connector": "fivetran",
        "database": "RAW",
        "schema": "HUBSPOT",
        "table": "CONTACTS",
        "load_strategy": "full_refresh",
        "cursor_field": None,
        "freshness_sla_hours": 24,
        "enabled": True,
    },
    {
        "name": "legacy_mysql_orders",
        "connector": "sftp",
        "database": "RAW",
        "schema": "LEGACY",
        "table": "ORDERS",
        "load_strategy": "full_refresh",
        "cursor_field": None,
        "freshness_sla_hours": 48,
        "enabled": False,  # decommissioned — proves the filter downstream works
    },
]

REQUIRED_KEYS = {
    "name",
    "connector",
    "database",
    "schema",
    "table",
    "load_strategy",
    "freshness_sla_hours",
    "enabled",
}


def validate(sources: list[dict]) -> list[dict]:
    """Fail loudly here rather than half way through the downstream task."""
    seen: set[str] = set()

    for i, source in enumerate(sources):
        missing = REQUIRED_KEYS - set(source)
        if missing:
            raise ValueError(f"source[{i}] is missing keys: {sorted(missing)}")

        name = source["name"]
        if name in seen:
            raise ValueError(f"duplicate source name: {name!r}")
        seen.add(name)

        if source["load_strategy"] not in {"incremental", "full_refresh"}:
            raise ValueError(
                f"{name}: load_strategy must be 'incremental' or 'full_refresh', "
                f"got {source['load_strategy']!r}"
            )

        if source["load_strategy"] == "incremental" and not source.get("cursor_field"):
            raise ValueError(f"{name}: incremental sources need a cursor_field")

    return sources


def main() -> int:
    api_key = os.environ.get("ORCHESTRA_API_KEY")
    if not api_key:
        print("ORCHESTRA_API_KEY not set — are we running inside an Orchestra task?")
        return 1

    orchestra = OrchestraSDK(api_key=api_key)

    validate(SOURCES)
    active = [s for s in SOURCES if s["enabled"]]

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pipeline_run_id": os.environ.get("ORCHESTRA_PIPELINE_RUN_ID", "local"),
        "sources": active,
    }

    print(f"Declared {len(SOURCES)} sources, {len(active)} enabled:")
    for source in active:
        print(
            f"  - {source['name']:<22} {source['connector']:<9} "
            f"{source['database']}.{source['schema']}.{source['table']} "
            f"({source['load_strategy']})"
        )
    for source in (s for s in SOURCES if not s["enabled"]):
        print(f"  - {source['name']:<22} SKIPPED (disabled)")

    # set_output returns False if the webhook call did not land — treat that as
    # a hard failure, otherwise the downstream task gets an empty env var and
    # fails with a much less obvious error.
    manifest_json = json.dumps(manifest)

    # Two channels for the same payload, on purpose:
    #   source_manifest      - raw JSON, readable in the Orchestra UI and usable
    #                          by anything that reads outputs via the API.
    #   source_manifest_bsix - base64 of the same JSON. This is the one the
    #                          downstream task consumes, because a task's
    #                          `environment_variables` field is itself a JSON
    #                          document: interpolating raw JSON (full of double
    #                          quotes) into it produces invalid JSON and the
    #                          task fails to start. Base64 is quote-safe.
    # (Output names may only contain letters and underscores, hence "bsix".)
    outputs = {
        "source_manifest": manifest_json,
        "source_manifest_bsix": base64.b64encode(manifest_json.encode()).decode(),
        "active_source_names": ",".join(s["name"] for s in active),
        "active_source_count": str(len(active)),
    }

    for name, value in outputs.items():
        if not orchestra.set_output(name=name, value=value):
            print(f"FAILED to set output {name!r}")
            return 1
        print(f"set_output({name!r}) ok ({len(value)} chars)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
