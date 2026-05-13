"""Run Orchestra pipelines via API using a config file."""

import argparse

from rich.panel import Panel

from _pipeline_runner_client import console, load_env_file, run_pipelines
from _pipeline_runner_config import load_config_file
from _pipeline_runner_output import print_summary


def main() -> None:
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
    console.print(f"[dim]Configured {len(workspaces_config)} workspace(s)[/dim]")

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
