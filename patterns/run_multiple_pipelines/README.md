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

## Two versions

The pattern ships in two forms. They read the same config and behave the same
way at the level that matters — validate everything up front, retry safely,
exit non-zero if a pipeline did not start.

| | `run_multiple_pipelines_minimal.py` | `run_multiple_pipelines.py` |
| --- | --- | --- |
| Files to copy | 1 | 2 |
| Lines of code | ~130 | ~440 |
| Dependencies | `requests`, `python-dotenv` | plus `rich` |
| Output | plain text | Rich table |
| Ambiguous outcomes | counted as failures | reported separately as `⚠ unknown` |
| Options | `--config`, `--env` | plus `--app-url`, `--max-retries` |

**Start with the minimal version.** It is the whole pattern in one file, and
it is enough for most uses. Reach for the fuller one if you want the nicer
terminal output, a non-default Orchestra URL, or to tell "this definitely did
not start" apart from "we never found out".

## Files

| File | Purpose |
| --- | --- |
| `run_multiple_pipelines_minimal.py` | Single-file version — self-contained |
| `run_multiple_pipelines.py` | Fuller version, CLI entrypoint |
| `_pipeline_runner.py` | Fuller version, shared helpers — copy alongside the entrypoint |
| `example.config.json` | Example config to copy and edit |
| `.env.example` | Example env file showing the token variable names |
| `requirements.txt` | Pinned dependencies for both versions |

## Usage

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a config JSON (see `example.config.json`) and run either version:

```bash
python run_multiple_pipelines_minimal.py --config path/to/config.json --env .env
```

```bash
python run_multiple_pipelines.py --config path/to/config.json --env .env
```

### Options

`--config` and `--env` work the same in both versions; the last two are
specific to `run_multiple_pipelines.py`.

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
