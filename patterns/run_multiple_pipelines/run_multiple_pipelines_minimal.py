#!/usr/bin/env python3
"""The same pattern as run_multiple_pipelines.py, in one short file.

Read this one first. It keeps only the behaviour that matters:

  * validates the whole config and resolves every API token *before* starting
    anything, so a typo in the last entry cannot strand already-started runs
  * retries rate limits, 5xx, and connection failures with backoff, but
    never a timeout, which could start the same pipeline twice
  * hides run_inputs values, which usually end up in CI logs
  * exits non-zero if any pipeline failed to start, so it is safe as a CI gate

It leaves out what the fuller version adds: rich terminal output, separate
handling for ambiguous outcomes, --app-url / --max-retries, and Retry-After
support.

"Started" means Orchestra accepted the request. It does NOT mean the run
finished successfully -- this script does not wait for that.

Requires: requests, python-dotenv

    python run_multiple_pipelines_minimal.py --config config.json --env .env
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

APP_URL = "https://app.getorchestra.io"
ENDPOINT = "/api/engine/public/pipelines/{identifier}/start"
TIMEOUT_SECONDS = 30
MAX_RETRIES = 3
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
OPTIONAL_FIELDS = ("branch", "commit", "environment")


class ConfigError(Exception):
    """The config file or the environment is unusable."""


def load_config(path: str) -> tuple[dict[str, str], list[dict[str, Any]]]:
    """Read and validate the entire config before anything is started."""
    try:
        config = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigError(f"Config file not found: {path}") from None
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid JSON in {path}: {e}") from None

    workspaces = config.get("workspaces") if isinstance(config, dict) else None
    pipelines = config.get("pipelines") if isinstance(config, dict) else None
    if not isinstance(workspaces, dict) or not workspaces:
        raise ConfigError("'workspaces' must be a non-empty JSON object")
    if not isinstance(pipelines, list) or not pipelines:
        raise ConfigError("'pipelines' must be a non-empty JSON array")

    for idx, entry in enumerate(pipelines, 1):
        if not isinstance(entry, dict):
            raise ConfigError(f"Pipeline entry {idx} must be a JSON object")
        for field in ("workspace", "pipeline"):
            value = entry.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ConfigError(
                    f"Pipeline entry {idx}: '{field}' must be a non-empty string",
                )
        if entry["workspace"] not in workspaces:
            raise ConfigError(
                f"Pipeline entry {idx} references workspace "
                f"'{entry['workspace']}', which is not defined in 'workspaces'",
            )
    return workspaces, pipelines


def resolve_tokens(
    workspaces: dict[str, str],
    pipelines: list[dict[str, Any]],
) -> dict[str, str]:
    """Look up every API token up front. Failing here costs nothing."""
    tokens, missing = {}, []
    for name in dict.fromkeys(entry["workspace"] for entry in pipelines):
        # A workspace maps to the NAME of an env var, not to the token itself.
        token = os.getenv(workspaces[name])
        if token:
            tokens[name] = token
        else:
            missing.append(f"  - workspace '{name}' needs {workspaces[name]}")
    if missing:
        raise ConfigError("Missing API token(s):\n" + "\n".join(missing))
    return tokens


def start_pipeline(entry: dict[str, Any], token: str) -> str:
    """Start one pipeline and return its run ID, or raise RuntimeError."""
    url = APP_URL + ENDPOINT.format(identifier=entry["pipeline"])
    headers = {"Authorization": f"Bearer {token}"}
    payload = {field: entry[field] for field in OPTIONAL_FIELDS if entry.get(field)}
    if entry.get("run_inputs"):
        payload["run_inputs"] = entry["run_inputs"]

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=TIMEOUT_SECONDS,
            )
            if response.ok:
                try:
                    run_id = response.json().get("pipelineRunId")
                except ValueError:
                    run_id = None
                if not run_id:
                    # The run was accepted but we cannot name it. The fuller
                    # version reports this separately; here it counts as a
                    # failure, so check Orchestra before re-running it.
                    raise RuntimeError("no 'pipelineRunId' in the response")
                return str(run_id)
            if response.status_code not in RETRYABLE_STATUS:
                raise RuntimeError(
                    f"HTTP {response.status_code}: {response.text[:200]}",
                )
            error = f"HTTP {response.status_code}"
        except requests.Timeout:
            # The request may already have been delivered, so a retry could
            # start the same pipeline twice. Stop and let a human check.
            raise RuntimeError(
                f"timed out after {TIMEOUT_SECONDS}s -- the run may have "
                f"started; check Orchestra before re-running",
            ) from None
        except requests.RequestException as e:
            error = f"request failed: {e}"

        if attempt == MAX_RETRIES:
            raise RuntimeError(f"{error} (gave up after {MAX_RETRIES} retries)")
        delay = 2**attempt
        print(f"    {error} - retrying in {delay}s")
        time.sleep(delay)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", required=True, help="Path to the JSON config")
    parser.add_argument("--env", help="Path to a .env file holding the API tokens")
    args = parser.parse_args(argv)

    try:
        env_path = args.env or (".env" if Path(".env").exists() else None)
        if env_path:
            if not Path(env_path).exists():
                raise ConfigError(f".env file not found: {env_path}")
            load_dotenv(env_path)
        workspaces, pipelines = load_config(args.config)
        tokens = resolve_tokens(workspaces, pipelines)
    except ConfigError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    failures = []
    for idx, entry in enumerate(pipelines, 1):
        print(f"[{idx}/{len(pipelines)}] {entry['pipeline']} ({entry['workspace']})")
        if entry.get("run_inputs"):
            # Values can carry secrets and this output often lands in CI logs.
            keys = ", ".join(entry["run_inputs"])
            print(f"    run_inputs: {keys} (values hidden)")
        try:
            run_id = start_pipeline(entry, tokens[entry["workspace"]])
        except RuntimeError as e:
            print(f"    FAILED: {e}")
            failures.append((entry, str(e)))
        else:
            print(f"    started, run ID {run_id}")

    started = len(pipelines) - len(failures)
    print(
        f"\n{started} started, {len(failures)} failed "
        f"('started' means accepted by Orchestra, not finished)",
    )
    for entry, error in failures:
        print(f"  failed: {entry['pipeline']} ({entry['workspace']}): {error}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
