"""Config file loading and validation for pipeline runner."""

import json
import sys
from typing import Any

from _pipeline_runner_client import console


def load_config_file(config_path: str) -> tuple[dict[str, str], list[dict[str, Any]]]:
    try:
        with open(config_path) as f:
            config = json.load(f)

        if not isinstance(config, dict):
            raise ValueError("Config file must contain a JSON object")

        workspaces = config.get("workspaces")
        if not workspaces:
            raise ValueError("Config file must contain a 'workspaces' field")
        if not isinstance(workspaces, dict):
            raise ValueError("'workspaces' must be a JSON object")
        if not workspaces:
            raise ValueError("'workspaces' cannot be empty")

        pipelines = config.get("pipelines")
        if not pipelines:
            raise ValueError("Config file must contain a 'pipelines' field")
        if not isinstance(pipelines, list):
            raise ValueError("'pipelines' must be a JSON array")
        if not pipelines:
            raise ValueError("'pipelines' cannot be empty")

        for idx, entry in enumerate(pipelines, 1):
            if not isinstance(entry, dict):
                raise ValueError(f"Pipeline entry {idx} must be a JSON object")
            if "pipeline" not in entry:
                raise ValueError(f"Pipeline entry {idx} is missing 'pipeline' field")
            if "workspace" not in entry:
                raise ValueError(f"Pipeline entry {idx} is missing 'workspace' field")
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
