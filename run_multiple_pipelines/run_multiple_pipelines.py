"""
Script to run Orchestra pipelines via the API using a config file.
Requires dotenv, requests, and rich (pip install dotenv requests rich)

Usage:
    python run_multiple_pipelines.py --config config.json --env prod.env

Example config.json:
    {
        "workspaces": {
            "workspace1": "ORCHESTRA_API_TOKEN_WS1",
            "workspace2": "ORCHESTRA_API_TOKEN_WS2"
        },
        "pipelines": [
            {
                "pipeline": "my_pipeline_alias",
                "workspace": "workspace1",
                "branch": "main",
                "commit": "abc123",
                "environment": "production",
                "run_inputs": {
                    "input1": "value1",
                    "input2": "value2"
                }
            },
            {
                "pipeline": "b52bd0f4-7799-47e2-982e-1e10608f64f0",
                "workspace": "workspace2",
                "environment": "staging",
                "run_inputs": {
                    "param": "test"
                }
            }
        ]
    }

Each pipeline entry must have "pipeline" (UUID or alias) and "workspace" fields.
Optional fields: "branch", "commit", "run_inputs", "environment"

Example prod.env:
    ORCHESTRA_API_TOKEN_WS1=your_token_for_workspace1
    ORCHESTRA_API_TOKEN_WS2=your_token_for_workspace2

--env is optional and will load environment variables from the .env file in the current directory.
"""

import argparse
import json
import os
import sys
import time
from typing import Any
from uuid import UUID

import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

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
    else:
        # Try to load .env from current directory if it exists
        if os.path.exists(".env"):
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

            # Handle 429 Too Many Requests with retry
            if response.status_code == 429:
                if attempt < max_retries:
                    console.print(
                        "[yellow]Rate limited (429). Waiting 60 seconds before retry...[/yellow]",
                    )
                    time.sleep(60)
                    console.print("[yellow]Retrying request...[/yellow]")
                    continue
                else:
                    error_msg = "HTTP 429: Too Many Requests (max retries exceeded)"
                    console.print(f"[red]Failed to start pipeline: {error_msg}[/red]")
                    response.raise_for_status()

            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            # Check if we have a response object and it's a 429
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

    # Should not reach here, but just in case
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
            f"\n[bold][{idx}/{total}] Pipeline: " f"{format_pipeline_identifier(pipeline)}[/bold]",
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


def print_summary(results: list[dict[str, Any]]):
    if not results:
        return

    table = Table(
        title="Pipeline Run Summary",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Pipeline", style="cyan", no_wrap=True)
    table.add_column("Workspace", style="yellow", no_wrap=True)
    table.add_column("Status", justify="center")
    table.add_column("Pipeline Run ID", style="dim")
    table.add_column("Environment", style="dim")
    table.add_column("Branch", style="dim")
    table.add_column("Commit", style="dim")
    table.add_column("Run Inputs", style="dim")

    for result in results:
        config = result.get("config", {})
        pipeline = config.get("pipeline", "Unknown")
        workspace = config.get("workspace", "Unknown")

        if result.get("success"):
            status = "[green]✓ Success[/green]"
            run_id = result.get("pipelineRunId", "N/A")
        else:
            status = "[red]✗ Failed[/red]"
            run_id = "N/A"

        environment = config.get("environment", "-")
        branch = config.get("branch", "-")
        commit = config.get("commit", "-")
        run_inputs = config.get("run_inputs")
        run_inputs_str = json.dumps(run_inputs) if run_inputs else ""

        table.add_row(
            pipeline,
            workspace,
            status,
            run_id,
            environment if environment != "-" else "",
            branch if branch != "-" else "",
            commit if commit != "-" else "",
            run_inputs_str,
        )

    console.print("\n")
    console.print(table)


def load_config_file(config_path: str) -> tuple[dict[str, str], list[dict[str, Any]]]:
    try:
        with open(config_path) as f:
            config = json.load(f)

        if not isinstance(config, dict):
            raise ValueError("Config file must contain a JSON object")

        # Validate workspaces
        workspaces = config.get("workspaces")
        if not workspaces:
            raise ValueError("Config file must contain a 'workspaces' field")
        if not isinstance(workspaces, dict):
            raise ValueError("'workspaces' must be a JSON object")
        if not workspaces:
            raise ValueError("'workspaces' cannot be empty")

        # Validate pipelines
        pipelines = config.get("pipelines")
        if not pipelines:
            raise ValueError("Config file must contain a 'pipelines' field")
        if not isinstance(pipelines, list):
            raise ValueError("'pipelines' must be a JSON array")
        if not pipelines:
            raise ValueError("'pipelines' cannot be empty")

        # Validate each pipeline entry
        for idx, entry in enumerate(pipelines, 1):
            if not isinstance(entry, dict):
                raise ValueError(f"Pipeline entry {idx} must be a JSON object")
            if "pipeline" not in entry:
                raise ValueError(
                    f"Pipeline entry {idx} is missing 'pipeline' field",
                )
            if "workspace" not in entry:
                raise ValueError(
                    f"Pipeline entry {idx} is missing 'workspace' field",
                )
            workspace = entry.get("workspace")
            if workspace not in workspaces:
                raise ValueError(
                    f"Pipeline entry {idx} references workspace '{workspace}' "
                    f"which is not defined in 'workspaces'",
                )

        return workspaces, pipelines
    except FileNotFoundError:
        console.print(f"[red]Error: Config file not found: {config_path}[/red]")
        sys.exit(1)
    except json.JSONDecodeError as e:
        console.print(f"[red]Error: Invalid JSON in config file: {e}[/red]")
        sys.exit(1)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Run Orchestra pipelines via the API using a config file",
    )
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to JSON config file with pipeline configurations",
    )
    parser.add_argument(
        "--env",
        type=str,
        default=None,
        help=(
            "Path to .env file containing API tokens "
            "(default: .env in current directory if exists)"
        ),
    )

    args = parser.parse_args()

    console.print(
        Panel.fit(
            "[bold blue]Orchestra Pipeline Runner[/bold blue]",
            border_style="blue",
        ),
    )

    load_env_file(args.env)
    workspaces_config, pipelines_config = load_config_file(args.config)
    console.print(
        f"[dim]Loaded {len(pipelines_config)} pipeline configuration(s) "
        f"from {args.config}[/dim]",
    )
    console.print(
        f"[dim]Configured {len(workspaces_config)} workspace(s)[/dim]",
    )
    results = run_pipelines(pipelines_config, workspaces_config)
    if results:
        print_summary(results)
        successes = sum(1 for r in results if r.get("success"))
        failures = len(results) - successes
        console.print(
            f"\n[bold]Total:[/bold] {len(results)} | "
            f"[green]Success:[/green] {successes} | "
            f"[red]Failed:[/red] {failures}",
        )


if __name__ == "__main__":
    main()
