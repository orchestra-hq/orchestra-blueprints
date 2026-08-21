"""Config loading, API client, and output helpers for the pipeline runner.

Kept in one module so the pattern reads top-to-bottom: parse config, resolve
tokens, start pipelines, print a summary.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

console = Console()

API_ENDPOINT_TEMPLATE = "/api/engine/public/pipelines/{identifier}/start"
DEFAULT_APP_URL = "https://app.getorchestra.io"
REQUEST_TIMEOUT_SECONDS = 30
DEFAULT_MAX_RETRIES = 3
MAX_RETRY_DELAY_SECONDS = 60
MAX_ERROR_DETAIL_CHARS = 200

# 429 and 5xx are safe to retry: the server answered, so the run did not start.
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


class ConfigError(Exception):
    """The config file, .env file, or environment is unusable."""


class PipelineStartError(Exception):
    """A pipeline could not be started.

    ``may_have_started`` marks the ambiguous cases -- the request reached
    Orchestra but we never saw a usable answer, so a blind re-run risks
    triggering the same pipeline twice.
    """

    def __init__(self, message: str, *, may_have_started: bool = False) -> None:
        super().__init__(message)
        self.may_have_started = may_have_started


@dataclass(frozen=True)
class PipelineConfig:
    """One validated entry from the config file's ``pipelines`` array."""

    workspace: str
    pipeline: str
    branch: str | None = None
    commit: str | None = None
    environment: str | None = None
    run_inputs: dict[str, Any] | None = None


@dataclass(frozen=True)
class RunResult:
    """The outcome of asking Orchestra to start one pipeline."""

    config: PipelineConfig
    started: bool
    pipeline_run_id: str | None = None
    error: str | None = None
    uncertain: bool = False


# --------------------------------------------------------------------------
# Environment and config loading
# --------------------------------------------------------------------------


def load_env_file(env_path: str | None) -> None:
    if env_path:
        path = Path(env_path)
        if not path.exists():
            raise ConfigError(f".env file not found: {path}")
        load_dotenv(path)
        console.print(f"[dim]Loaded environment variables from {path}[/dim]")
    elif Path(".env").exists():
        load_dotenv(".env")
        console.print("[dim]Loaded environment variables from .env[/dim]")


def _require_str(value: Any, description: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{description} must be a non-empty string")
    return value.strip()


def _parse_pipeline_entry(
    entry: Any,
    idx: int,
    workspaces: dict[str, str],
) -> PipelineConfig:
    where = f"Pipeline entry {idx}"
    if not isinstance(entry, dict):
        raise ConfigError(f"{where} must be a JSON object")

    workspace = _require_str(entry.get("workspace"), f"{where}: 'workspace'")
    if workspace not in workspaces:
        raise ConfigError(
            f"{where} references workspace '{workspace}' "
            f"which is not defined in 'workspaces'",
        )

    pipeline = _require_str(entry.get("pipeline"), f"{where}: 'pipeline'")
    if any(char in pipeline for char in "/?#"):
        raise ConfigError(
            f"{where}: 'pipeline' must be a UUID or an alias, not a URL path "
            f"(got {pipeline!r})",
        )

    run_inputs = entry.get("run_inputs")
    if run_inputs is not None and not isinstance(run_inputs, dict):
        raise ConfigError(f"{where}: 'run_inputs' must be a JSON object")

    optional: dict[str, str] = {}
    for name in ("branch", "commit", "environment"):
        value = entry.get(name)
        if value is not None:
            optional[name] = _require_str(value, f"{where}: '{name}'")

    return PipelineConfig(
        workspace=workspace,
        pipeline=pipeline,
        run_inputs=run_inputs,
        **optional,
    )


def load_config(config_path: str) -> tuple[dict[str, str], list[PipelineConfig]]:
    """Read and fully validate the config file.

    Every entry is validated before any pipeline is started, so a typo in the
    last entry cannot leave the first few already running.
    """
    path = Path(config_path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigError(f"Config file not found: {path}") from None
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid JSON in config file: {e}") from None

    if not isinstance(raw, dict):
        raise ConfigError("Config file must contain a JSON object")

    workspaces_raw = raw.get("workspaces")
    if not isinstance(workspaces_raw, dict):
        raise ConfigError("Config file must contain a 'workspaces' JSON object")
    if not workspaces_raw:
        raise ConfigError("'workspaces' cannot be empty")
    workspaces = {
        _require_str(name, "Workspace name"): _require_str(
            env_var,
            f"workspaces.{name}",
        )
        for name, env_var in workspaces_raw.items()
    }

    pipelines_raw = raw.get("pipelines")
    if not isinstance(pipelines_raw, list):
        raise ConfigError("Config file must contain a 'pipelines' JSON array")
    if not pipelines_raw:
        raise ConfigError("'pipelines' cannot be empty")

    pipelines = [
        _parse_pipeline_entry(entry, idx, workspaces)
        for idx, entry in enumerate(pipelines_raw, 1)
    ]
    return workspaces, pipelines


def resolve_tokens(
    workspaces: dict[str, str],
    pipelines: list[PipelineConfig],
) -> dict[str, str]:
    """Resolve every API token up front, before the first pipeline starts.

    Failing here is cheap. Failing halfway through the run is not: pipelines
    already triggered would be lost from the summary.
    """
    tokens: dict[str, str] = {}
    missing: list[str] = []

    for workspace in dict.fromkeys(config.workspace for config in pipelines):
        env_var = workspaces[workspace]
        token = os.getenv(env_var)
        if token:
            tokens[workspace] = token
        else:
            missing.append(f"  - workspace '{workspace}' needs {env_var}")

    if missing:
        raise ConfigError(
            "Missing API token environment variable(s):\n"
            + "\n".join(missing)
            + "\nSet them in your .env file or your runtime secret manager.",
        )
    return tokens


# --------------------------------------------------------------------------
# API client
# --------------------------------------------------------------------------


def is_uuid(value: str) -> bool:
    try:
        UUID(value)
    except (ValueError, AttributeError, TypeError):
        return False
    return True


def format_pipeline_identifier(identifier: str) -> str:
    if is_uuid(identifier):
        return f"[cyan]{identifier}[/cyan]"
    return f"[green]{identifier}[/green] (alias)"


def _build_payload(config: PipelineConfig) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if config.branch:
        payload["branch"] = config.branch
    if config.commit:
        payload["commit"] = config.commit
    if config.run_inputs:
        payload["run_inputs"] = config.run_inputs
    if config.environment:
        payload["environment"] = config.environment
    return payload


def _loggable_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Redact run_inputs values, which often carry credentials.

    This output usually ends up in CI logs, so log the keys and not the values.
    """
    safe = dict(payload)
    if "run_inputs" in safe:
        safe["run_inputs"] = dict.fromkeys(safe["run_inputs"], "***")
    return safe


def _error_message(response: requests.Response) -> str:
    message = f"HTTP {response.status_code}"
    try:
        body = response.json()
    except ValueError:
        detail: Any = response.text.strip()
    else:
        detail = body.get("detail") if isinstance(body, dict) else None
    if detail:
        message += f": {str(detail)[:MAX_ERROR_DETAIL_CHARS]}"
    return message


def _retry_after_seconds(response: requests.Response) -> float | None:
    """Honour a numeric Retry-After header; ignore the HTTP-date form."""
    raw = response.headers.get("Retry-After")
    if not raw:
        return None
    try:
        return min(float(raw), MAX_RETRY_DELAY_SECONDS)
    except ValueError:
        return None


def _extract_run_id(response: requests.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        raise PipelineStartError(
            "pipeline was accepted but the response was not JSON, "
            "so no run ID could be recorded",
            may_have_started=True,
        ) from None

    run_id = body.get("pipelineRunId") if isinstance(body, dict) else None
    if not run_id:
        raise PipelineStartError(
            "pipeline was accepted but the response contained no 'pipelineRunId'",
            may_have_started=True,
        )
    return str(run_id)


def start_pipeline(
    config: PipelineConfig,
    api_token: str,
    app_url: str = DEFAULT_APP_URL,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> str:
    """Ask Orchestra to start one pipeline and return its pipeline run ID.

    Returning normally means the run was *accepted*, not that it succeeded.
    Retries cover rate limits, 5xx, and connection failures -- never a read
    timeout, which could mean the run started and we simply did not hear back.
    """
    url = f"{app_url.rstrip('/')}{API_ENDPOINT_TEMPLATE.format(identifier=config.pipeline)}"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }
    payload = _build_payload(config)

    console.print(f"[dim]POST {url}[/dim]")
    if payload:
        console.print(
            f"[dim]Payload: {json.dumps(_loggable_payload(payload))}[/dim]",
        )

    for attempt in range(max_retries + 1):
        retry_after: float | None = None
        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except requests.exceptions.ConnectTimeout as e:
            error = f"connection timed out: {e}"
        except requests.exceptions.ReadTimeout as e:
            # The request was delivered; retrying could double-trigger the run.
            raise PipelineStartError(
                f"timed out after {REQUEST_TIMEOUT_SECONDS}s waiting for a "
                f"response: {e}",
                may_have_started=True,
            ) from None
        except requests.exceptions.ConnectionError as e:
            error = f"connection failed: {e}"
        except requests.RequestException as e:
            raise PipelineStartError(f"request failed: {e}") from None
        else:
            if response.ok:
                return _extract_run_id(response)
            error = _error_message(response)
            if response.status_code not in RETRYABLE_STATUS_CODES:
                raise PipelineStartError(error)
            retry_after = _retry_after_seconds(response)

        if attempt == max_retries:
            raise PipelineStartError(
                f"{error} (gave up after {max_retries} retr"
                f"{'y' if max_retries == 1 else 'ies'})",
            )

        delay = retry_after if retry_after is not None else min(2**attempt, 30)
        console.print(
            f"[yellow]{error} -- retrying in {delay:.0f}s "
            f"({attempt + 1}/{max_retries})[/yellow]",
        )
        time.sleep(delay)


def _print_request_details(config: PipelineConfig) -> None:
    console.print(f"[dim]Workspace: {config.workspace}[/dim]")
    for label, value in (
        ("Branch", config.branch),
        ("Commit", config.commit),
        ("Environment", config.environment),
    ):
        if value:
            console.print(f"[dim]{label}: {value}[/dim]")
    if config.run_inputs:
        keys = ", ".join(config.run_inputs)
        console.print(f"[dim]Run Inputs: {keys} (values redacted)[/dim]")


def run_pipelines(
    pipelines: list[PipelineConfig],
    tokens: dict[str, str],
    app_url: str = DEFAULT_APP_URL,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> list[RunResult]:
    """Start each pipeline in turn, collecting one RunResult per entry."""
    results: list[RunResult] = []
    total = len(pipelines)

    console.print(f"\n[bold]Starting {total} pipeline(s)...[/bold]\n")

    for idx, config in enumerate(pipelines, 1):
        console.print(
            f"\n[bold][{idx}/{total}] Pipeline: "
            f"{format_pipeline_identifier(config.pipeline)}[/bold]",
        )
        _print_request_details(config)

        try:
            run_id = start_pipeline(
                config,
                tokens[config.workspace],
                app_url,
                max_retries,
            )
        except PipelineStartError as e:
            if e.may_have_started:
                console.print(f"[yellow]⚠ Outcome unknown: {e}[/yellow]")
                console.print(
                    "[yellow]  Check Orchestra before re-running -- this "
                    "pipeline may already be running.[/yellow]",
                )
            else:
                console.print(f"[red]✗ Failed to start: {e}[/red]")
            results.append(
                RunResult(
                    config=config,
                    started=False,
                    error=str(e),
                    uncertain=e.may_have_started,
                ),
            )
        else:
            console.print("[green]✓ Pipeline started[/green]")
            console.print(f"[dim]Pipeline Run ID: {run_id}[/dim]")
            results.append(
                RunResult(config=config, started=True, pipeline_run_id=run_id),
            )

    return results


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------


def _status_cell(result: RunResult) -> str:
    if result.started:
        return "[green]✓ started[/green]"
    if result.uncertain:
        return "[yellow]⚠ unknown[/yellow]"
    return "[red]✗ failed[/red]"


def _details_cell(config: PipelineConfig) -> str:
    """Fold the optional overrides into one column so the table stays legible."""
    parts = []
    for label, value in (
        ("env", config.environment),
        ("branch", config.branch),
        ("commit", config.commit),
    ):
        if value:
            parts.append(f"{label}={value}")
    if config.run_inputs:
        parts.append(f"inputs={','.join(config.run_inputs)}")
    return " ".join(parts)


def print_summary(results: list[RunResult]) -> None:
    if not results:
        return

    table = Table(
        title="Pipeline Trigger Summary",
        show_header=True,
        header_style="bold magenta",
        caption=(
            "'✓ started' means Orchestra accepted the request. "
            "It does not mean the run has finished successfully."
        ),
    )
    table.add_column("Pipeline", style="cyan", overflow="fold")
    table.add_column("Workspace", style="yellow")
    table.add_column("Trigger", justify="center", no_wrap=True)
    table.add_column("Pipeline Run ID", style="dim", overflow="fold")
    table.add_column("Details", style="dim", overflow="fold")

    for result in results:
        table.add_row(
            result.config.pipeline,
            result.config.workspace,
            _status_cell(result),
            result.pipeline_run_id or "",
            _details_cell(result.config),
        )

    console.print("\n")
    console.print(table)
