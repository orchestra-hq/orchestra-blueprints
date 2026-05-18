---
name: dlt-source-via-orchestra
description: Build a new dlt source that lands API data into MotherDuck, then ship it through Orchestra. Use this when the user wants to "pull X from <API> into MotherDuck" or "add a new dlt source and run it on Orchestra". Walks the full lifecycle on a feature branch — author the source, register an Orchestra pipeline that invokes it, trigger the pipeline against that branch, and poll until done.
---

# Build & ship a dlt → MotherDuck source via Orchestra

Use this end-to-end when adding a new API → MotherDuck source. The dlt code goes
in `python/dlt/`; the Orchestra pipeline that runs it goes in `orchestra/`. The
pipeline must be runnable against the feature branch before it lands on `main`,
so every step is parameterised by the branch created in step 1.

## Steps

### 1. Create a feature branch
From `main`, cut a branch named `feat/dlt-<source>` (e.g. `feat/dlt-linear`).
Save the branch name verbatim — you will pass it to `start_pipeline` in step 7
and substitute it into the Python task in step 4. Step 8 promotes the staged
load into prod, so make sure the prod DB name set in step 3 is the one the user
actually wants overwritten.

```bash
git checkout main && git pull
git checkout -b feat/dlt-<source>
```

**If the source already exists on `main`** (i.e. you're "rebuilding" or
re-running a previously merged pipeline): cut a `-v2`/`-rerun` branch and
**keep the existing `python/dlt/<source>/`, `<source>_pipeline.py`, and
`orchestra/<source>_to_motherduck.yml` files as-is** — skip ahead to step 5.
"Rebuild" in this context means re-register and re-trigger on a fresh branch,
not delete and re-author working code. Only rewrite files if the user
explicitly says the existing code is broken or that they want it replaced.

### 2. Identify the source endpoints
Read the source's API docs (or call `WebFetch` on them) to determine:
- Which endpoint(s) yield the entities the user asked for.
- Pagination style: cursor (`pageInfo.endCursor`), offset, link headers, or `next` URLs.
- Server-side filtering for the requested window (e.g. `updatedAt >= now-7d`). Do
  the filter in the API request, not client-side — keeps the load small.
- Auth mechanism: header name (`Authorization: <token>` vs `Bearer <token>`),
  query-string token, OAuth.

Write these down before coding — guessing pagination or filter syntax wastes a
full dlt run.

### 3. Locate credentials and set destination env vars
Both the source API and MotherDuck must be reachable from env vars (Orchestra
injects them via the Python integration's `environment_variables`). Probe for
likely names before writing code:

```powershell
[Environment]::GetEnvironmentVariables('User').Keys |
  Where-Object { $_ -match '<source>|motherduck|md_' }
```

**Credential env vars (must already exist — never hardcode):**
- MotherDuck: `MOTHERDUCK_API_TOKEN` (also accepted as `MOTHERDUCK_TOKEN`).
- Source API: e.g. `LINEAR_API_KEY`, `HUBSPOT_API_KEY`.

If a credential is missing, stop and ask the user — do not hardcode.

**Destination env vars (set defaults if unset, then promote to the Process env
so the local validation in step 7 and the Orchestra task config pick them up).
The pattern is: dlt lands into a **staging** database, prod is overwritten by
the step-8 COPY only after the load looks clean:**

| Var | Purpose | Default |
| --- | ------- | ------- |
| `<SOURCE>_MD_PROD_DATABASE`    | Final destination (overwritten by step 8) | `my_db` |
| `<SOURCE>_MD_STAGING_DATABASE` | Where dlt lands first | `<prod>_staging` (e.g. `my_db_staging`) |
| `<SOURCE>_MD_DATASET`          | Target schema (dlt `dataset_name`) | `dlt_<source>` |

PowerShell — set only if not already present:

```powershell
if (-not $env:<SOURCE>_MD_PROD_DATABASE)    { $env:<SOURCE>_MD_PROD_DATABASE    = 'my_db' }
if (-not $env:<SOURCE>_MD_STAGING_DATABASE) { $env:<SOURCE>_MD_STAGING_DATABASE = "$($env:<SOURCE>_MD_PROD_DATABASE)_staging" }
if (-not $env:<SOURCE>_MD_DATASET)          { $env:<SOURCE>_MD_DATASET          = 'dlt_<source>' }
```

These three env vars flow through all the later steps unchanged — step 6
snapshots `<SOURCE>_MD_PROD_DATABASE`, the Python script in step 4a writes to
`<SOURCE>_MD_STAGING_DATABASE`, the Orchestra task in step 4c passes all three
through `environment_variables`, and step 8 reads both database names when
building the `COPY FROM DATABASE` SQL. Keep the names consistent across local
shell, Python script, YAML task, and MCP calls.

### 4. Author the dlt source AND the Orchestra YAML

**4a. Code under `python/dlt/<source>/`:**

- `python/dlt/<source>/__init__.py` — `@dlt.source` and `@dlt.resource` definitions,
  using `dlt.sources.helpers.requests` for HTTP. Resource should be
  `write_disposition="merge"` with the API's stable primary key, and accept a
  `since_days` argument that translates into the server-side filter.
- `python/dlt/<source>_pipeline.py` — wires env vars and runs the pipeline:
  - Pulls `MOTHERDUCK_API_TOKEN` and the source token from `os.environ`.
  - Reads destination from env:
    `database = os.environ.get("<SOURCE>_MD_STAGING_DATABASE", "my_db_staging")`,
    `dataset  = os.environ.get("<SOURCE>_MD_DATASET", "dlt_<source>")`.
  - Sets `DESTINATION__MOTHERDUCK__CREDENTIALS=md:<staging_database>?motherduck_token=<token>`.
  - Calls `dlt.pipeline(pipeline_name="<source>", dataset_name=dataset, destination="motherduck")`.
  - `LINEAR_SINCE_DAYS`-style env var for the window (default 7 in `__main__`).

The script writes to **staging** only — it must never read `<SOURCE>_MD_PROD_DATABASE`.
Prod is touched exclusively by the step-8 COPY task; keeping that separation
means a half-failed load only corrupts staging, and step 6's snapshot of prod
is a clean rollback point.

**4b. Add any new packages to `python/dlt/requirements.txt`:**

Orchestra's Python integration runs `pip install -r requirements.txt` in the
checked-out repo. The dlt MotherDuck extra is mandatory for this pattern and is
not pulled in by `dlt[bigquery]`:

```
dlt[motherduck]==1.16.0
```

Pin the version to the same line as the other `dlt[...]` extras so the resolver
picks one consistent dlt build. If the source needs a vendor SDK (e.g.
`hubspot-api-client`), add it here too.

**4c. Orchestra pipeline at `orchestra/<source>_to_motherduck.yml`:**

The pipeline has a single PYTHON_EXECUTE_SCRIPT task. The two non-obvious bits:

1. **Top-level `inputs.branch.default: main`** declares a branch override that
   defaults to `main`, so a scheduled run on `main` keeps working.
2. **`branch: ${{ inputs.branch }}`** on the Python task wires that override
   into the integration. At trigger time, `start_pipeline(branch=<feature>)`
   replaces it.

Skeleton (let the `orchestra-pipeline` skill generate the full YAML; this is
just the shape). Two stages: Python load → MotherDuck promote. The promote is
wired into the pipeline as a `MOTHERDUCK_EXECUTE_QUERY` task that depends on
the Python stage, so prod is updated atomically as part of each run and there
is no separate manual MCP `COPY FROM DATABASE` step.

```yaml
version: v1
name: '<source> to MotherDuck #dlt #motherduck'
pipeline:
  <python-stage-uuid>:
    tasks:
      <python-task-uuid>:
        integration: PYTHON
        integration_job: PYTHON_EXECUTE_SCRIPT
        parameters:
          package_manager: PIP
          python_version: '3.11'
          build_command: pip install -r requirements.txt
          source: GIT
          branch: ${{ inputs.branch }}
          command: python -m <source>_pipeline
          project_dir: python/dlt
          shallow_clone_dirs: python/dlt
          environment_variables: '{
            "<SOURCE>_SINCE_DAYS": "${{ inputs.since_days }}",
            "<SOURCE>_MD_STAGING_DATABASE": "${{ inputs.md_staging_database }}",
            "<SOURCE>_MD_PROD_DATABASE":    "${{ inputs.md_prod_database }}",
            "<SOURCE>_MD_DATASET":          "${{ inputs.md_dataset }}"
            }'
          set_outputs: true
        depends_on: []
        name: Run <source> dlt
        connection: python__production__blueprints__19239
    depends_on: []
    name: ''
  <promote-stage-uuid>:
    tasks:
      <promote-task-uuid>:
        integration: MOTHERDUCK
        integration_job: MOTHERDUCK_EXECUTE_QUERY
        parameters:
          query: "COPY FROM DATABASE ${{ inputs.md_staging_database }} TO ${{ inputs.md_prod_database }} (SCHEMA '${{ inputs.md_dataset }}', OVERWRITE);"
          set_outputs: false
        depends_on: []
        name: Promote staging to prod
    depends_on:
    - <python-stage-uuid>
    name: ''
inputs:
  branch:
    type: string
    default: main
  since_days:
    type: string
    default: '7'
  md_staging_database:
    type: string
    default: my_db_staging
  md_prod_database:
    type: string
    default: my_db
  md_dataset:
    type: string
    default: dlt_<source>
```

Tokens (`MOTHERDUCK_API_TOKEN`, source key) come from the connection's
environment, not `environment_variables` in the YAML — never inline secrets.

### 5. Register the pipeline with Orchestra
Commit the YAML + Python code to the feature branch and push. Then use the
Orchestra MCP `import_pipeline` tool with the YAML contents to register it. The
tool returns the pipeline UUID — save it (you need it for step 7 and for any
future re-runs).

```
mcp__orchestramcp__import_pipeline(yaml="<contents of orchestra/<source>_to_motherduck.yml>")
```

If the pipeline already exists at the same alias, this updates it in place.

### 6. Prepare staging and snapshot prod
Two MotherDuck MCP `query_rw` calls before the pipeline runs:

```
mcp__MotherDuck__query_rw(
  sql="CREATE DATABASE IF NOT EXISTS <md_staging_database>"
)

mcp__MotherDuck__query_rw(
  sql="CREATE SNAPSHOT <source>_pre_<YYYYMMDD_HHMMSS> OF <md_prod_database>"
)
```

The first ensures dlt has somewhere to land — MotherDuck will not auto-create
the database, only schemas within it. The second is a point-in-time, read-only
copy of prod; pick a deterministic snapshot name tied to this run (e.g.
`linear_pre_20260518_141500`). If step 8's promote goes wrong, `RESTORE` prod
from this snapshot instead of re-syncing from the source.

Both database names come from the env vars set in step 3 — substitute them
into the SQL string before sending to MCP. If either call fails (database
doesn't exist, snapshot name collision), stop and surface the error. Don't
proceed to a load that has no rollback point.

### 7. Trigger on the feature branch and poll
Trigger the pipeline against the branch from step 1, then poll until terminal.

```
mcp__orchestramcp__start_pipeline(alias="<pipeline-uuid>", branch="<feature-branch>")
mcp__orchestramcp__get_pipeline_run_status(pipeline_run_id="<run-uuid>")
```

Poll `get_pipeline_run_status` until the status is not `RUNNING` or `CREATED`.
Report the terminal status and surface the Orchestra UI link:

```
https://app.getorchestra.io/pipeline-runs/<run-uuid>/lineage
```

On failure, call `list_task_runs` (filtered by the run UUID) to find the FAILED
task, then `download_task_run_log` for its log. The most common causes:
- `requirements.txt` missing the new extra (e.g. `dlt[motherduck]`) → the
  `motherduck` destination import errors out. Fix step 4b and retrigger.
- Env var name mismatch between the script and the connection's env config →
  rename in `<source>_pipeline.py` to match the connection. Applies to credential
  vars and `<SOURCE>_MD_STAGING_DATABASE` / `<SOURCE>_MD_PROD_DATABASE` /
  `<SOURCE>_MD_DATASET`.
- API rate-limit / 401 → token is missing from the connection's env config, not
  a code bug.
- Load partially corrupted an existing dataset → `RESTORE` from the snapshot
  created in step 6, then fix the bug and re-run.

Once the run is green on the feature branch, the staging database holds the
fresh load. Prod is still untouched — promote it in step 8.

### 8. Verify the promote
The promote ran as the `MOTHERDUCK_EXECUTE_QUERY` task in step 4c, scoped to
the `${{ inputs.md_dataset }}` schema via `(SCHEMA '<md_dataset>', OVERWRITE)`.
`OVERWRITE` drops tables in `<prod>` that also exist in `<staging>` before
recopying — anything in prod outside the `<md_dataset>` schema is left alone.

Once the pipeline run is green end-to-end (Python stage SUCCEEDED, promote
stage SUCCEEDED), spot-check the prod result via the MotherDuck MCP:

```
mcp__MotherDuck__query(database="<md_prod_database>",
  sql="SELECT COUNT(*) FROM <md_dataset>.<main_table>")
mcp__MotherDuck__query(database="<md_prod_database>",
  sql="SELECT MIN(updated_at), MAX(updated_at) FROM <md_dataset>.<main_table>")
```

If the promote stage failed but the Python stage succeeded, staging holds the
correct data and prod is untouched — re-run only the promote stage from the
Orchestra UI (or re-trigger the whole pipeline; `OVERWRITE` is idempotent). If
the COPY itself corrupted prod, `RESTORE` from the snapshot taken in step 6.

Once both stages are green on the feature branch, the YAML and Python code are
ready to merge to `main`.

## Notes
- The promote in step 8 is wired into the pipeline as a
  `MOTHERDUCK_EXECUTE_QUERY` task that depends on the Python stage — it runs
  automatically on every trigger, no manual MCP call required. The pre-load
  snapshot in step 6 is still a manual MCP step; consider promoting it into
  the YAML as a third `MOTHERDUCK_EXECUTE_QUERY` task (no `depends_on`, with
  the Python task gaining `depends_on: [<snapshot-stage>]`) once the pattern
  is proven on the source.
- Staging vs prod: dlt should never write directly to prod. The split exists
  so a half-failed load only corrupts staging (which is rebuilt every run),
  and prod only changes via the atomic `COPY FROM DATABASE … (OVERWRITE)` in
  step 8. If you find yourself reaching for `<SOURCE>_MD_PROD_DATABASE` in
  the Python script, stop — that's the smell that the split is being bypassed.
- The Python task uses `shallow_clone_dirs: python/dlt` so the integration only
  pulls that subtree — adding files outside `python/dlt/` won't slow checkout.
- `branch` on the Python task is the canonical way to scope a run to a feature
  branch. `start_pipeline`'s `branch` argument overrides the whole pipeline's
  `inputs.branch`, including the dbt and other Git-aware tasks if you later add
  them. Don't try to override per-task.
- See `fix-and-rerun-pipeline` for the failure-diagnosis loop once the pipeline
  exists. See `orchestra-pipeline` (built-in) for full YAML generation against
  the documented schema.
