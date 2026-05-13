"""API and execution helpers for the pipeline runner."""

import json
import os
import sys
import time
from typing import Any
from uuid import UUID

import requests
from dotenv import load_dotenv
from rich.console import Console

console = Console()

API_ENDPOINT_TEMPLATE = "/api/engine/public/pipelines/{identifier}/start"
APP_URL = "https://app.getorchestra.io"


def is_uuid(value: str) -> bool:
    try:
        UUID(value)
        return True
    except ValueError:
        return False


def load_env_file(env_path: str | None) -> None:
    if env_path:
        if not os.path.exists(env_path):
            console.print(f"[red]Error: .env file not found: {env_path}[/red]")
            sys.exit(1)
        load_dotenv(env_path)
        console.print(f"[dim]Loaded environment variables from {env_path}[/dim]")
    elif os.path.exists(".env"):
        load_dotenv(".env")
        console.print("[dim]Loaded environment variables from .env[/dim]")


def get_api_token(workspace: str, workspaces_config: dict[str, str]) -> str:
    env_var_name = workspaces_config.get(workspace)
    if not env_var_name:
        console.print(
            f"[red]Error: Workspace '{workspace}' not found in workspaces configuration.[/red]",
        )
        sys.exit(1)

    token = os.getenv(env_var_name)
    if not token:
        console.print(
            f"[red]Error: Environment variable '{env_var_name}' "
            f"is not set for workspace '{workspace}'.[/red]",
        )
        console.print(
            f"[yellow]Please set it in your .env file: {env_var_name}=your_token[/yellow]",
        )
        sys.exit(1)
    return token


def start_pipeline(
    pipeline_identifier: str,
    api_token: str,
    branch: str | None = None,
    commit: str | None = None,
    run_inputs: dict[str, Any] | None = None,
    environment: str | None = None,
    max_retries: int = 1,
) -> dict[str, Any]:
    url = f"{APP_URL.rstrip('/')}{API_ENDPOINT_TEMPLATE.format(identifier=pipeline_identifier)}"

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    payload: dict[str, Any] = {}
    if branch:
        payload["branch"] = branch
    if commit:
        payload["commit"] = commit
    if run_inputs:
        payload["run_inputs"] = run_inputs
    if environment:
        payload["environment"] = environment

    console.print(f"[dim]POST {url}[/dim]")
    if payload:
        console.print(f"[dim]Payload: {json.dumps(payload, indent=2)}[/dim]")

    for attempt in range(max_retries + 1):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code == 429:
                if attempt < max_retries:
                    console.print(
                        "[yellow]Rate limited (429). Waiting 60 seconds before retry...[/yellow]",
                    )
                    time.sleep(60)
                    console.print("[yellow]Retrying request...[/yellow]")
                    continue
                error_msg = "HTTP 429: Too Many Requests (max retries exceeded)"
                console.print(f"[red]Failed to start pipeline: {error_msg}[/red]")
                response.raise_for_status()

            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if hasattr(e, "response") and e.response is not None:
                if e.response.status_code == 429 and attempt < max_retries:
                    console.print(
                        "[yellow]Rate limited (429). Waiting 60 seconds before retry...[/yellow]",
                    )
                    time.sleep(60)
                    console.print("[yellow]Retrying request...[/yellow]")
                    continue
                error_msg = f"HTTP {e.response.status_code}"
                try:
                    error_body = e.response.json()
                    if "detail" in error_body:
                        error_msg += f": {error_body['detail']}"
                except Exception:
                    error_msg += f": {e.response.text}"
            else:
                error_msg = f"HTTP Error: {str(e)}"
            console.print(f"[red]Failed to start pipeline: {error_msg}[/red]")
            raise
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Request failed: {str(e)}[/red]")
            raise

    raise Exception("Failed to start pipeline after retries")


def format_pipeline_identifier(identifier: str) -> str:
    if is_uuid(identifier):
        return f"[cyan]{identifier}[/cyan]"
    return f"[green]{identifier}[/green] (alias)"


def run_pipelines(
    configs: list[dict[str, Any]],
    workspaces_config: dict[str, str],
) -> list[dict[str, Any]]:
    results = []
    total = len(configs)

    console.print(f"\n[bold]Running {total} pipeline(s)...[/bold]\n")

    for idx, config in enumerate(configs, 1):
        pipeline = config.get("pipeline")
        if not pipeline:
            console.print(
                f"[red]Error: Pipeline identifier missing in config {idx}[/red]",
            )
            continue

        workspace = config.get("workspace")
        if not workspace:
            console.print(
                f"[red]Error: Workspace missing in config {idx}[/red]",
            )
            continue

        branch = config.get("branch")
        commit = config.get("commit")
        run_inputs = config.get("run_inputs")
        environment = config.get("environment")

        console.print(
            f"\n[bold][{idx}/{total}] Pipeline: "
            f"{format_pipeline_identifier(pipeline)}[/bold]",
        )
        console.print(f"[dim]Workspace: {workspace}[/dim]")

        if branch:
            console.print(f"[dim]Branch: {branch}[/dim]")
        if commit:
            console.print(f"[dim]Commit: {commit}[/dim]")
        if environment:
            console.print(f"[dim]Environment: {environment}[/dim]")
        if run_inputs:
            console.print(f"[dim]Run Inputs: {json.dumps(run_inputs, indent=2)}[/dim]")

        try:
            api_token = get_api_token(workspace, workspaces_config)
            result = start_pipeline(
                pipeline,
                api_token,
                branch,
                commit,
                run_inputs,
                environment,
            )
            result["config"] = config
            result["success"] = True
            results.append(result)

            pipeline_run_id = result.get("pipelineRunId", "N/A")
            console.print("[green]✓ Pipeline started successfully[/green]")
            console.print(f"[dim]Pipeline Run ID: {pipeline_run_id}[/dim]")

        except Exception as e:
            console.print(f"[red]✗ Failed to start pipeline: {str(e)}[/red]")
            results.append(
                {
                    "config": config,
                    "success": False,
                    "error": str(e),
                },
            )

    return results
