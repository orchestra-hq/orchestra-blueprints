# Dummy Python pipeline

A deliberately minimal example used to demonstrate the **register → run → promote**
CI/CD flow for git-backed Orchestra pipelines.

| File | Purpose |
| --- | --- |
| `dummy_script.py` | Stdlib-only script the pipeline executes. Prints a few log lines and exits 0. |
| `../../orchestra/dummy_python_pipeline.yml` | One task group, one `PYTHON_EXECUTE_SCRIPT` task. |
| `../../.github/workflows/dummy_pipeline_register_run_promote.yaml` | Registers the pipeline, runs it, and promotes it to a second workspace on success. |
| `../../scripts/orchestra_register_pipeline.sh` | Idempotent `orchestra import` wrapper shared by both workspaces. |

## The flow

1. **Register** — `orchestra import` registers `orchestra/dummy_python_pipeline.yml`
   in the *source* workspace under the alias `dummy-python-pipeline`. The wrapper
   script checks the alias first, because every `orchestra import` call creates a
   new pipeline and would otherwise produce duplicates.
2. **Run** — `orchestra run --wait` triggers the pipeline against the current
   branch and commit, then polls until a terminal state. `FAILED`/`CANCELLED`
   exits non-zero and fails the job.
3. **Promote** — only if step 2 was green, the same YAML is registered in the
   *target* workspace using that workspace's own API key. Orchestra workspaces
   are fully isolated, so promotion is an import with a different key rather than
   a copy operation.

## Required GitHub secrets

Both live on the `production` GitHub environment:

- `ORCHESTRA_API_KEY` — standard API key for the source (dev/staging) workspace.
- `ORCHESTRA_TARGET_API_KEY` — standard API key for the target (production) workspace.

Read-only keys will not work: `import` and `run` are write operations.

## Target workspace prerequisites

Because workspaces share nothing, the target workspace needs, in its own right:

- a git connection to this repository, and
- a `PYTHON` connection matching the `connection` field in the pipeline YAML
  (currently `python__production__blueprints__19239`). If the target workspace
  names its connection differently, parameterise it as
  `connection: ${{ ENV.PYTHON_CONNECTION }}` and set that environment variable
  per workspace.

## Testing the promote gate

Set `FAIL_ON_PURPOSE` to `true` in the task's `environment_variables` and run the
workflow. The run fails, and the `promote` job is skipped — which is the point.
