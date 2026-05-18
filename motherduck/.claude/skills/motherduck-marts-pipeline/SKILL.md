---
name: motherduck-marts-pipeline
description: Step 1 of the MotherDuck-on-Orchestra workflow. Profile live MotherDuck source data (not checked-in sql/*.sql), propose an analytics mart model (facts/dims, grains, key metrics), then ship the SQL as Orchestra MOTHERDUCK_EXECUTE_QUERY tasks appended into the pipeline the user names — ingest already lives there; do not regenerate ingest tasks. Use when turning raw source tables into mart tables, extending a pipeline the user linked (alias, ID, or URL), iterating on mart shape, or diagnosing failed runs. When the user names a target pipeline for ingest or says add work into it, extend that pipeline without asking new vs extend. Outputs sql/<alias>.sql, pipelines/<alias>.yaml, a live Orchestra pipeline, and a successful run. Pair with motherduck-dive-from-question for Step 2 and motherduck-orchestra-analysis for the end-to-end question → marts → Dive flow.
---

# MotherDuck source → Orchestra marts pipeline

This skill drives Step 1 of a two-step workflow:

1. **Step 1 (this skill)** — analyse MotherDuck source data, propose a mart
   model, ship an Orchestra pipeline that builds those marts.
2. **Step 2** — `motherduck-dive-from-question`: interrogate the marts with a
   user analytics question and publish a Dive that answers it.

For the full question → marts → Dive path in one user message, start from
`motherduck-orchestra-analysis`.

The two step skills are deliberately separable. Step 1 is durable infra (marts +
pipeline); Step 2 is the per-question answer artefact.

## When to invoke

- "Build a pipeline that turns `<source_db>.<source_schema>` into marts."
- "Profile this MotherDuck schema and propose facts/dims."
- "My Orchestra pipeline `<alias>` is failing — diagnose and fix."
- "Add a `fct_<thing>` table to the marts pipeline."
- "I'm ingesting metadata in this pipeline — add mart work into it: `<url>`"

Skip if the user only wants to *query* MotherDuck — that doesn't need a
pipeline. Skip if they want to author a Dive only — that's Step 2 (or the
orchestrator when marts already exist).

## Required context (ask if missing)

| Input | Default | Notes |
| ----- | ------- | ----- |
| MotherDuck database | — | E.g. `my_db`. Required. |
| Source schema | — | E.g. `orchestra_metadata_app`. Required. |
| Target marts schema | `<source_db>.orchestra_marts` | Hardcoded in SQL (Orchestra templating gotcha — see below). |
| Orchestra MotherDuck connection ID | look up via Orchestra MCP if missing | E.g. `md_my_db_09250`. Exposed as pipeline input `motherduck_connection_id`. |
| Pipeline alias / ID / URL | — | Required when extending. Parse Orchestra URLs; use `list_pipelines` when needed. No repo default. |

If the user gives a vague brief ("build marts from my Orchestra metadata"),
profile first and propose the model back to them before authoring.

Do **not** read `sql/*.sql` in this repo as the mart specification — derive
the model from live MotherDuck introspection (`references/profile_checklist.md`).

## Decide: new pipeline or extend an existing one?

This decision is **mandatory** and must be settled before authoring SQL.
Don't silently default to a new pipeline — users very often want the new
transformations dropped into an existing pipeline, especially if there's
already a Step-1 pipeline in `pipelines/` building related marts.

### Read the signals first

- **Prompt language**: "add", "append", "extend", "wire into", "drop into",
  "tack on to <name>", "ingesting … in this pipeline", plus a pipeline URL,
  alias, or ID → **extend that pipeline**; skip the new-vs-extend question.
- "Build", "create new", "start a new" → new pipeline unless they also named
  a specific pipeline to extend.
- **Repo state**: `ls pipelines/*.yaml`. If exactly one exists and the user
  hasn't named a different target, that's the default extension target.
  Multiple → must ask which.
- **Orchestra state**: `mcp__orchestra__list_pipelines` is the authoritative
  source if the user references a pipeline not in `pipelines/` locally.
- **The user named a specific group / location**: "add these as a new
  `customer_marts` group", "stick them after the dbt task" — they're
  extending, and they've told you the insertion point.

### If still ambiguous, ask via `AskUserQuestion`

```
Question: "Build a new Orchestra pipeline for these marts, or extend an existing one?"
Header: "Pipeline target"
Options:
  - "Extend <alias> (Recommended)"   ← when exactly one local pipeline exists
        → preserves Dive wiring; new tasks appended as a new group
  - "Build a new pipeline"
        → fresh alias, fresh YAML, fresh create_pipeline
  - "Extend a different pipeline"
        → list other Orchestra pipelines, pick one
```

If the user named the target pipeline in their prompt, skip the prompt and
go straight to authoring.

### Where do the new tasks sit when extending?

| User intent | Insertion |
| ----------- | --------- |
| "Append to the end" / unspecified | New task group at the end of `pipeline:`, `depends_on: [<previous-last-group>]`. |
| Named target group (existing) | Add as sibling tasks inside that group; set per-task `depends_on` within the group as needed. |
| Named target group (new) | Insert a new group at the named position; rewire `depends_on` on any group that previously depended on what now must wait. |
| "Run in parallel with the build" | New group with the same `depends_on` as the existing build group. Pick this only if the user explicitly says so — most marts have implicit FK dependencies. |

**Critical rule**: if the pipeline already has a `publish-dive` task group
(this is true for any pipeline shipped via the Step 2 skill's wiring step),
the new marts group must run **before** `publish-dive`, AND `publish-dive`
must depend on the new group. Otherwise the Dives republish against stale
marts. When inserting:

1. Find the existing `publish-dive` group.
2. Insert the new group with `depends_on: [<previous-last-build-group>]`.
3. Append the new group's name to `publish-dive.depends_on`.

Don't touch existing task IDs — Orchestra task-run history is keyed on them
and Dive consumers might depend on names. Add, don't rename.

## Workflow

### 1. Profile the source schema (MotherDuck MCP)

Use these tools in parallel:

- `mcp__MotherDuck__list_tables` for `<source_db>.<source_schema>`.
- `mcp__MotherDuck__list_columns` on each candidate table.
- `mcp__MotherDuck__query` for sample rows (`LIMIT 5`), distinct counts on
  candidate keys, null rates on important columns, min/max timestamps to
  understand the time window.

For each table, decide: **dim or fact?** Dims describe entities (one row per
thing, slowly changing); facts describe events (one row per occurrence, with
measures + foreign keys to dims).

Watch for child tables (e.g. `<table>__owners`, `<table>__upstream_dependencies`)
from a DLT-style flattening — these are array fields that need to be aggregated
back into the parent dim (see `references/mart_patterns.md` for the DLT child-table
flattening pattern).

### 2. Propose the mart model — confirm with the user

Before writing SQL, summarise:

```
- dim_<entity>     grain: one row per <entity>          measures: …
- fct_<event>      grain: one row per <event>           measures: …
- fct_<rollup>     grain: one row per (day, dim, dim)   derived from fct_<event>
```

For each, list the source table(s), the grain, and 2–4 headline measures. Get
the user to confirm or amend. Don't go silent — name what you're going to build.

### 3. Write the SQL reference file

Drop a single reference script at `sql/<alias>.sql` with `CREATE OR REPLACE
TABLE <db>.<marts_schema>.<table_name> AS …` for every mart. This documents
what the pipeline runs — it is **not** the spec you design from; that comes
from step 1 profiling.

Conventions:
- Fully-qualified table names (`<db>.<marts_schema>.<table>`) — Orchestra's
  templating doesn't interpolate inside SQL strings (see gotcha below), so
  hardcode the schema.
- `GROUP BY ALL` and `ORDER BY ALL` are fine — DuckDB-native.
- `COUNT(*) FILTER (WHERE …)` for status splits.
- `DATEDIFF('second', started_at, completed_at)` for durations.
- `STRING_AGG(value, ', ' ORDER BY _dlt_list_idx)` for ordered list flattening.

### 4. Write or extend the pipeline YAML

Branch on the decision from "Decide: new pipeline or extend an existing one?":

- **New pipeline** → write a fresh YAML at `pipelines/<alias>.yaml`. Use the
  three-task-group shape below.
- **Extend an existing pipeline** → load `pipelines/<existing-alias>.yaml`,
  insert the new task group at the agreed insertion point, rewrite the file.
  Don't rename existing keys; only add (and possibly amend `depends_on` on a
  downstream `publish-dive` group). Use the merge recipe below the new-pipeline
  template.

#### 4a. New-pipeline template

```yaml
version: v1
name: <Human Name>
inputs:
  motherduck_connection_id:
    type: string
    default: <md_…>
    optional: false
pipeline:
  create-schema:
    name: ''
    depends_on: []
    tasks:
      create-mart-schema:
        integration: MOTHERDUCK
        integration_job: MOTHERDUCK_EXECUTE_QUERY
        connection: ${{ inputs.motherduck_connection_id }}
        name: Create mart schema
        depends_on: []
        parameters:
          query: |
            CREATE SCHEMA IF NOT EXISTS <db>.<marts_schema>;
  build-tables:
    name: ''
    depends_on: [create-schema]
    tasks:
      build-dim-<x>:
        integration: MOTHERDUCK
        integration_job: MOTHERDUCK_EXECUTE_QUERY
        connection: ${{ inputs.motherduck_connection_id }}
        name: Build dim_<x>
        depends_on: []          # within-group dependency
        parameters:
          query: |
            CREATE OR REPLACE TABLE <db>.<marts_schema>.dim_<x> AS …;
      # repeat for each mart; intra-group depends_on for derived tables
schedule: []
```

Notes that bite if ignored:
- **Task-group name and task name must not collide.** A task with the same ID
  as its containing group gets rejected with "Task with ID: X is actually a
  TaskGroup and cannot be executed". When in doubt, name groups by *phase*
  (`build-tables`) and tasks by *target* (`build-fct-pipeline-run`).
- `depends_on` at the task-group level orchestrates groups; at the task level
  it orchestrates within the group only.
- `set_outputs: true` on a task means its rows are persisted as the task's
  output (useful for the Dive-publish step in Step 2).
- Templating only resolves when the *whole* field value is the template (e.g.
  `connection: ${{ inputs.motherduck_connection_id }}` works; embedded
  `${{ inputs.x }}` inside a SQL string does NOT — see
  `orchestra-pipeline-via-api` for the full write-up). Hardcode schema /
  database names in SQL.

#### 4b. Extending an existing pipeline

Use a Python helper (the YAML can be 40kb+ with base64 dive payloads — Edit
tool is impractical). Standard recipe:

```python
import yaml
from pathlib import Path

p = Path("pipelines/<existing-alias>.yaml")
data = yaml.safe_load(p.read_text())
pipeline = data["pipeline"]

# 1. Determine the insertion point.
new_group_name = "build-<topic>-marts"     # or whatever fits
previous_group = "<last build group>"      # from existing keys
publish_group_name = "publish-dive"        # if it exists

# 2. Build the new group.
pipeline[new_group_name] = {
    "name": "",
    "depends_on": [previous_group],
    "tasks": {
        "build-dim-<x>": {
            "integration": "MOTHERDUCK",
            "integration_job": "MOTHERDUCK_EXECUTE_QUERY",
            "connection": "${{ inputs.motherduck_connection_id }}",
            "name": "Build dim_<x>",
            "depends_on": [],
            "parameters": {"query": "CREATE OR REPLACE TABLE <db>.<schema>.dim_<x> AS …;"},
        },
        # …more tasks
    },
}

# 3. If publish-dive exists, make it wait for the new group too.
if publish_group_name in pipeline:
    deps = pipeline[publish_group_name].setdefault("depends_on", [])
    if new_group_name not in deps:
        deps.append(new_group_name)

# 4. Write back. sort_keys=False to preserve declaration order;
#    width is huge so base64 query lines don't wrap.
p.write_text(yaml.safe_dump(data, sort_keys=False, width=10**9))
```

When the user named a specific insertion point (e.g. "add as a task inside
`build-tables`"), skip the new-group step and add tasks directly to the
existing group's `tasks` dict instead. Keep `depends_on` within the group
explicit if the new task should wait for sibling outputs.

After mutating the YAML, **also append the new `CREATE OR REPLACE TABLE`
statements to `sql/<alias>.sql`** — the SQL reference file must stay in sync
with what the pipeline runs, or the next reader will get a misleading source
of truth.

### 5. Validate + deploy via Orchestra MCP

Always MCP-first. Convert the YAML to a Python dict, then:

1. `mcp__orchestra__validate_pipeline pipeline_definition=<data>` — should
   return `{"message": "Pipeline schema is valid"}`. Surface any errors back
   to the user before deploying.
2. **Route on the new vs extend decision**:
   - **New pipeline** → `mcp__orchestra__create_pipeline alias=<alias> data=<data> published=True storage_provider="ORCHESTRA"`.
   - **Extending an existing pipeline** → `mcp__orchestra__update_pipeline alias=<existing-alias> data=<data> published=True storage_provider="ORCHESTRA"`. Do NOT call create — it'll fail on duplicate alias, and if it somehow succeeded you'd get two pipelines diverging in production.

If those MCP tools aren't loaded, `ToolSearch` first
(`+orchestra +pipeline`) before falling back to REST. The
`orchestra-pipeline-via-api` skill has the REST endpoints + auth pattern.

**REST-fallback gotcha**: when PUT-ing via REST, the body shape is `{"data":
<dict>, "published": true}` — **omit `storage_provider`**. The PUT endpoint
rejects it as `extra_forbidden` (it's accepted on POST/create only). The MCP
`update_pipeline` wrapper handles this for you; the gotcha only bites the
REST path.

### 6. Start + monitor the run

1. `mcp__orchestra__start_pipeline alias_or_pipeline_id=<alias> run_inputs={}`.
   (Inputs already have defaults; only pass overrides.)
2. Poll `mcp__orchestra__get_pipeline_run_status pipeline_run_id=<id>` until
   terminal. Warm runs finish in ~25–60s; a cold MotherDuck warehouse can take
   several minutes on the `create-schema` step. If it hangs >15 min, retry.
3. On failure, `mcp__orchestra__list_task_runs pipeline_ids=<id> time_from=… time_to=…`
   (≤168h window) and read the `externalMessage` of the failing task — it's
   the verbatim DuckDB error. Also inspect `taskParameters.query` for the
   rendered SQL.

### 7. Spot-check the marts

Use `mcp__MotherDuck__query` to confirm each mart has rows and the headline
measures look sensible. Common quick checks:

```sql
SELECT COUNT(*), MIN(<ts>), MAX(<ts>) FROM <db>.<marts_schema>.fct_<x>;
SELECT <status_col>, COUNT(*) FROM <db>.<marts_schema>.fct_<x> GROUP BY 1;
```

If something is empty, suspect a join column mismatch or a stale upstream
load (the marts are only as fresh as the source DLT import).

### 8. Hand off to Step 2

Tell the user the pipeline is live and propose Step 2:

> "Marts are built. Ask me a question about this data and I'll author + publish
> a MotherDuck Dive that answers it (Step 2 — `motherduck-dive-from-question`)."

## Iterating on an existing pipeline

If the user wants to add or change a mart:

1. Edit `sql/<alias>.sql` and `pipelines/<alias>.yaml`.
2. Re-validate and `update_pipeline` (NOT create).
3. Start a run, monitor, spot-check.

Don't touch the `publish-dive` task if one exists from Step 2 — leave that to
the dive skill. If the new marts change column names the Dive depends on,
flag it explicitly so Step 2 can re-author the TSX.

## Gotchas (cross-referenced)

| Gotcha | Where it bites | Fix |
| ------ | -------------- | --- |
| `${{ inputs.x }}` doesn't substitute inside SQL strings | parameters.query | Hardcode db/schema names; only use templating on whole-field sinks like `connection`. |
| Orchestra splits MOTHERDUCK queries on `;` | Multi-statement SQL is fine; payloads with embedded `;` (TSX, JSON) are not. | For SQL, this is benign. For non-SQL payloads (relevant in Step 2), base64-encode. |
| Task ID collides with group ID | Validate fails with "Task with ID: X is actually a TaskGroup…" | Rename one of them. |
| Cancelling a run doesn't stop the in-flight SQL | `MD_CREATE_DIVE` keeps going after cancel | Wait for the SQL or clean up after with `MD_DELETE_DIVE`. |
| Cold MotherDuck warehouse | First `CREATE SCHEMA` can hang several minutes | Patience; retry only after ~15 min. |

For the full write-ups see `orchestra-pipeline-via-api` (Orchestra side) and
`motherduck-dive-publishing` (MotherDuck side).

## See also

- `orchestra-pipeline-via-api` — wire-level Orchestra mechanics, REST fallback,
  templating + split-on-`;` gotchas.
- `motherduck-orchestra-analysis` — end-to-end question → marts → Dive.
- `motherduck-dive-from-question` — Step 2 of this workflow.
- `references/profile_checklist.md` — quick MCP-call checklist for source
  profiling.
- `references/mart_patterns.md` — reusable SQL patterns (status splits, DLT
  child-table flattening, daily rollups).
