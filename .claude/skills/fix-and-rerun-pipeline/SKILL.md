---
name: fix-and-rerun-pipeline
description: Given a failed Orchestra pipeline run ID, this skill automates the full workflow of diagnosing the failure, applying a code fix on a new GitHub branch, and re-running the pipeline on that branch.
---



## Steps

### 1. Get pipeline run status
Use the Orchestra MCP `get_pipeline_run_status` tool with the provided pipeline run ID to confirm it has failed.

### 2. Get task runs to find root cause
Use `list_task_runs` filtered by the pipeline ID to get all task runs for the failed run. Identify the FAILED task(s) and read the `externalMessage` field for detailed error output (e.g. dbt logs, stack traces). Note any SKIPPED tasks — these are downstream victims of the failure, not the root cause.

### 3. Diagnose the failure
Analyse the error output to determine:
- **Is it a code issue?** (e.g. dbt test failure, broken model, bad SQL) → proceed to fix in GitHub
- **Is it a tool/infrastructure issue?** (e.g. Fivetran sync error, connection failure) → surface the relevant platform URL using the `platformLink` or `connectionId` from the task run, and stop here

### 4. Fix the code in a new GitHub branch
If the failure is a code issue:
- Find the GitHub token in env vars (`GITHUB_TOKEN` or `GITHUB_API_TOKEN`)
- Fetch the relevant file(s) from the repo via GitHub API (`GET /repos/{owner}/{repo}/contents/{path}`)
- Apply the minimal fix needed. Examples:
  - dbt `not_null` test failing due to NULLs in data → change severity to `warn` with `warn_if: ">= {failure_count}"` rather than removing the test
  - Broken SQL → fix the model
- Get the SHA of the main branch HEAD (`GET /repos/{owner}/{repo}/git/ref/heads/main`)
- Create a new branch: `POST /repos/{owner}/{repo}/git/refs` with ref `refs/heads/fix/{short-description}`
- Commit the fix: `PUT /repos/{owner}/{repo}/contents/{path}` with the new content, file SHA, and branch name

### 5. Re-run the pipeline on the new branch
Use the Orchestra MCP `start_pipeline` tool:
- `alias`: the pipeline ID (UUID)
- `branch`: the new branch name created in step 4

### 6. Poll until completion
Repeatedly call `get_pipeline_run_status` with the new pipeline run ID until the status is no longer `RUNNING` or `CREATED`. Report the final status and surface the Orchestra UI link:
```
https://app.getorchestra.io/pipeline-runs/{pipeline_run_id}/lineage
```

## Notes
- GitHub token is in env var `GITHUB_TOKEN`
- Pipeline runs are triggered by pipeline ID (UUID), not alias
- The `branch` parameter in `start_pipeline` overrides the branch for the entire pipeline run
- Always prefer fixing tests with appropriate severity/thresholds over removing them
- If the pipeline is paused, `start_pipeline` will return a 400 — ask the user to unpause it in the Orchestra UI and retry
