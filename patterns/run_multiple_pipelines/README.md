# Run Multiple Pipelines (Orchestra Platform Pattern)

This is an **Orchestra-as-a-platform** pattern: it starts several Orchestra
pipeline runs from a single JSON config file, then prints a summary of which
requests were accepted.

It is not designed to be invoked as a single task module by Orchestra during a
pipeline run. Instead, use it as a helper to trigger (or audit) other pipelines
programmatically.

> **This is a trigger tool, not a monitor.** The script asks Orchestra to start
> each pipeline and reports whether that request was accepted. It does **not**
> wait for the runs to finish. A `✓ started` row means the run was queued — the
> pipeline may still fail minutes later. To gate a downstream step on the
> outcome, poll each returned pipeline run ID, or use Orchestra's own
> dependency and alerting features.

## Files

Copy **all** of these together — the entrypoint imports the shared module:

| File | Purpose |
| --- | --- |
| `run_multiple_pipelines.py` | CLI entrypoint |
| `_pipeline_runner.py` | Config loading, API client, and output helpers |
| `example.config.json` | Example config to copy and edit |
| `.env.example` | Example env file showing the token variable names |
| `requirements.txt` | Pinned dependencies |

## Usage

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a config JSON (see `example.config.json`) and run:

```bash
python run_multiple_pipelines.py --config path/to/config.json --env .env
```

### Options

| Flag | Default | Purpose |
| --- | --- | --- |
| `--config` | *required* | Path to the JSON config file |
| `--env` | `.env` if present | Path to a `.env` file holding the API tokens |
| `--app-url` | `https://app.getorchestra.io` | Orchestra base URL |
| `--max-retries` | `3` | Retries per pipeline for rate limits, 5xx, and connection failures |

## Config file

```json
{
    "workspaces": {
        "production": "PROD_API_TOKEN"
    },
    "pipelines": [
        {
            "workspace": "production",
            "pipeline": "daily-ingest",
            "branch": "main"
        }
    ]
}
```

**`workspaces`** maps a workspace label you choose to the **name of the
environment variable** holding that workspace's Orchestra API key — not the key
itself. Above, the runner reads the token from `$PROD_API_TOKEN`. Keep real
tokens in your `.env` file or runtime secret manager, never in the config file.

**`pipelines`** is a list of runs to start. Each entry takes:

| Field | Required | Notes |
| --- | --- | --- |
| `workspace` | yes | Must match a key in `workspaces` |
| `pipeline` | yes | Pipeline UUID or alias |
| `branch` | no | Git branch to run |
| `commit` | no | Git commit SHA to run |
| `environment` | no | Orchestra environment name |
| `run_inputs` | no | Object of run input values |

The whole config is validated before any pipeline is started, so a typo in the
last entry will not leave the first few already running.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Every pipeline was accepted |
| `1` | At least one pipeline failed to start, or its outcome is unknown |
| `2` | Bad arguments, bad config file, or a missing API token |

Safe to use as a CI gate: a failed trigger fails the step.

## Notes on behaviour

- **Retries.** Rate limits (429), 5xx responses, and connection failures are
  retried with exponential backoff, honouring `Retry-After` when the server
  sends it. A read timeout is deliberately **not** retried — the request may
  have been delivered, and retrying could start the same pipeline twice.
- **Unknown outcomes.** If a request is delivered but no usable response comes
  back, the run is reported as `⚠ unknown` rather than failed. Check Orchestra
  before re-running those entries.
- **Logging.** `run_inputs` keys are logged but their values are redacted, since
  this output usually lands in CI logs.
