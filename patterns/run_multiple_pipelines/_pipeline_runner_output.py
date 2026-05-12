"""Rich output formatting helpers for pipeline runner."""

import json
from typing import Any

from rich.table import Table

from _pipeline_runner_client import console


def print_summary(results: list[dict[str, Any]]) -> None:
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
