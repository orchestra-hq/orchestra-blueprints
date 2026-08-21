"""Start several Orchestra pipeline runs from one JSON config file.

This is a trigger tool: it asks Orchestra to start each pipeline and reports
whether each request was accepted. It does not wait for the runs to finish, so
a green summary means "accepted", not "succeeded".

Exits non-zero if any pipeline failed to start, or if any outcome is unknown.
"""

from __future__ import annotations

import argparse
import sys

from rich.panel import Panel

from _pipeline_runner import (
    DEFAULT_APP_URL,
    DEFAULT_MAX_RETRIES,
    ConfigError,
    console,
    load_config,
    load_env_file,
    print_summary,
    resolve_tokens,
    run_pipelines,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Start Orchestra pipeline runs via the API using a JSON config "
            "file. Does not wait for the runs to complete."
        ),
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to JSON config file with pipeline configurations",
    )
    parser.add_argument(
        "--env",
        default=None,
        help=(
            "Path to .env file containing API tokens "
            "(default: .env in the current directory, if it exists)"
        ),
    )
    parser.add_argument(
        "--app-url",
        default=DEFAULT_APP_URL,
        help=f"Orchestra base URL (default: {DEFAULT_APP_URL})",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=DEFAULT_MAX_RETRIES,
        help=(
            "Retries per pipeline for rate limits, 5xx, and connection "
            f"failures (default: {DEFAULT_MAX_RETRIES})"
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    console.print(
        Panel.fit(
            "[bold blue]Orchestra Pipeline Runner[/bold blue]",
            border_style="blue",
        ),
    )

    if args.max_retries < 0:
        console.print("[red]Error: --max-retries cannot be negative[/red]")
        return 2

    # Load, validate, and resolve every token before starting anything, so a
    # bad config or missing token cannot strand already-triggered runs.
    try:
        load_env_file(args.env)
        workspaces, pipelines = load_config(args.config)
        tokens = resolve_tokens(workspaces, pipelines)
    except ConfigError as e:
        console.print(f"[red]Error: {e}[/red]")
        return 2

    console.print(
        f"[dim]Loaded {len(pipelines)} pipeline configuration(s) "
        f"from {args.config}[/dim]",
    )
    console.print(f"[dim]Configured {len(workspaces)} workspace(s)[/dim]")

    results = run_pipelines(pipelines, tokens, args.app_url, args.max_retries)
    print_summary(results)

    started = sum(1 for result in results if result.started)
    unknown = sum(1 for result in results if result.uncertain)
    failed = len(results) - started - unknown

    console.print(
        f"\n[bold]Total:[/bold] {len(results)} | "
        f"[green]Started:[/green] {started} | "
        f"[yellow]Unknown:[/yellow] {unknown} | "
        f"[red]Failed:[/red] {failed}",
    )

    if failed or unknown:
        console.print(
            "\n[red]One or more pipelines did not start. See the summary above.[/red]",
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
