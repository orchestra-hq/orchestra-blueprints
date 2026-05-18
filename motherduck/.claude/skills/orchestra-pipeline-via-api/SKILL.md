---
name: orchestra-pipeline-via-api
description: Create, update, validate, and run Orchestra pipelines without going through a GitHub-backed import. Use this whenever the user wants to ship a pipeline that lives outside an Orchestra-imported Git repo (e.g. uncommitted local YAML, dynamic generation from a script, or fast iteration on pipeline shape). Also use when diagnosing pipeline runs, navigating Orchestra's templating quirks, or working around Orchestra's hard split-on-semicolon for query parameters. **Prefer Orchestra MCP tools first** (`create_pipeline`, `update_pipeline`, `validate_pipeline`, `list_pipelines`) — they're the cleanest path. Fall back to the public REST API only when those MCP tools aren't surfaced.
---

# Orchestra pipelines without GitHub

Use this when you want to author/maintain Orchestra pipelines as JSON (or YAML
converted to JSON) and ship them directly to Orchestra without going through a
GitHub-backed import. This avoids the round-trip of pushing to `main` for every
small iteration.

## ALWAYS try MCP tools first

The user's local Orchestra MCP server (`~/orchestra-mcp/orchestramcp/server.py`)
exposes pipeline-management tools that wrap the REST API. **Use these by
default** — they're shorter, don't need API-key handling, and avoid the SSL
quirks of Mac framework Python.

| Purpose | MCP tool | Args |
| ------- | -------- | ---- |
| Validate schema | `mcp__orchestra__validate_pipeline` | `pipeline_definition` (dict — the `data` object) |
| List pipelines | `mcp__orchestra__list_pipelines` | (none) |
| Create pipeline | `mcp__orchestra__create_pipeline` | `alias`, `data`, `published=False`, `storage_provider="ORCHESTRA"` |
| Update pipeline | `mcp__orchestra__update_pipeline` | `alias`, `data`, `published=False`, `storage_provider="ORCHESTRA"` |
| Import from GitHub | `mcp__orchestra__import_pipeline` | (Git-backed only) |
| Start a run | `mcp__orchestra__start_pipeline` | `alias_or_pipeline_id`, `run_inputs={...}` |
| Status | `mcp__orchestra__get_pipeline_run_status` | `pipeline_run_id` |
| Diagnose | `mcp__orchestra__list_task_runs` | `pipeline_ids`, `time_from`, `time_to` |

If an MCP tool doesn't appear in your tool registry, do NOT immediately fall
back to the REST API — first try `ToolSearch` with `query: "+orchestra +pipeline"`
(plural variants too: `+pipelines`). Older MCP server versions may need a
restart to expose newly-added tools; if a restart isn't possible, then fall
back.

## REST API fallback

Only use this when the MCP tools above genuinely aren't available. Same shape
as the MCP wrappers, but you handle auth + transport yourself.

## The four endpoints you need

All endpoints use:
```
Authorization: Bearer $ORCHESTRA_API_KEY
Content-Type: application/json
Host: app.getorchestra.io
```

Read `$ORCHESTRA_API_KEY` from `~/.claude/mcp.json` (`mcpServers.orchestra.env.ORCHESTRA_API_KEY`) — the same key the Orchestra MCP uses.

| Purpose | Method + path | Notes |
| ------- | ------------- | ----- |
| Validate pipeline schema | `POST /api/engine/public/pipelines/schema` | No auth needed; rate-limited to 20/min/IP. Body is the pipeline `data` object directly (no wrapper). Returns `{"message":"Pipeline schema is valid"}` on success. |
| Create pipeline | `POST /api/engine/public/pipelines` | Body: `{"alias": "<name>", "published": true, "storage_provider": "ORCHESTRA", "data": {...pipeline...}}`. Returns `id`, `alias`, `latestVersionNumber`. |
| Update pipeline | `PUT /api/engine/public/pipelines/{alias}` | Body: `{"data": {...pipeline...}, "published": true}`. Bumps `latestVersionNumber`. |
| Start a run | `POST /api/engine/public/pipelines/{alias_or_id}/start` | Body: `{"runInputs": {...}}` (camelCase!). Or use `mcp__orchestra__start_pipeline` (MCP tool, snake_case `run_inputs`). |

`alias` constraints: letters, numbers, underscores only. Max 255 chars.

## The pipeline `data` object

This is the same structure as the YAML you'd put in a Git repo, parsed as
JSON. Top-level keys: `version` (string `"v1"`), `name`, `inputs` (map),
`pipeline` (map of task-groups → `{tasks: {...}, depends_on: [...], name: ""}`),
`schedule` (list).

A task looks like:
```json
{
  "integration": "MOTHERDUCK",
  "integration_job": "MOTHERDUCK_EXECUTE_QUERY",
  "connection": "${{ inputs.motherduck_connection_id }}",
  "name": "Build dim_pipeline",
  "depends_on": ["create-mart-schema"],
  "parameters": {
    "query": "CREATE OR REPLACE TABLE ...",
    "set_outputs": true
  }
}
```

Note: Orchestra's API normalises `integration_job` → `integrationJob` and
`depends_on` → `dependsOn` in the persisted form, but accepts either on input.

## Standard authoring loop (MCP-first)

1. Edit `pipelines/<alias>.yaml` locally.
2. Parse to a Python dict / JSON object (`yaml.safe_load(...)`).
3. `mcp__orchestra__validate_pipeline pipeline_definition=<data>` — should return
   `{"message": "Pipeline schema is valid"}` or surface the API error.
4. First time: `mcp__orchestra__create_pipeline alias=<x> data=<...> published=true`.
   Subsequent updates: `mcp__orchestra__update_pipeline alias=<x> data=<...> published=true`.
5. Trigger: `mcp__orchestra__start_pipeline alias_or_pipeline_id=<alias> run_inputs={...}`.
6. Monitor: `mcp__orchestra__get_pipeline_run_status pipeline_run_id=<id>`.
7. Diagnose: `mcp__orchestra__list_task_runs pipeline_ids=<id> time_from=... time_to=...` (≤168h apart).

If `create_pipeline` / `update_pipeline` aren't available in your tool
registry, fall back to the REST endpoints in the next section — but try the
MCP tools first.

For long task-run lists, prefer `time_from`/`time_to` filters narrow enough to
keep the response under the tool's token cap. If it overflows, use `jq` on the
saved file rather than reading directly.

## Templating gotcha: `${{ inputs.x }}` only resolves at the field level

Orchestra resolves `${{ inputs.x }}` ONLY when the *entire field value* is the
template — e.g.:

```yaml
connection: ${{ inputs.motherduck_connection_id }}      # ✅ resolves to "md_my_db_09250"
```

It does NOT resolve when the template is *embedded inside* a longer string,
even though the docs example implies it does. These all FAIL:

```yaml
parameters:
  query: "CREATE SCHEMA IF NOT EXISTS ${{ inputs.mart_schema }};"   # ❌ literal "${{...}}" reaches DuckDB
content: "User question: ${{ inputs.analytics_question }}"          # ❌ literal in LLM prompts
```

Workarounds:
- **Hardcode** the value in the YAML (works for things that rarely change, like
  schema names). Keep the input definition for documentation, even if unused.
- **Generate the YAML** from a script that interpolates inputs at YAML-build
  time, then re-PUT the pipeline.
- For values that *must* be runtime inputs (e.g. an analytics question), expose
  them as a separate top-level field that Orchestra's templating *does* honour
  (e.g. `connection`), or accept that the LLM prompt will see the literal token
  and design around it (rarely the right answer).

The `connection` field is the only obvious "whole-field" sink in the public
schema, so practically: assume parameters are static at PUT time.

## Statement-splitting gotcha: Orchestra splits MOTHERDUCK queries on `;`

Orchestra's MOTHERDUCK_EXECUTE_QUERY task splits the `query` parameter on `;`
and runs each chunk via `connection.execute()`. There is *no* user-facing
`split_statements: false` knob. Consequences:

- Multi-statement scripts (`CREATE SCHEMA ...; CREATE TABLE ...;`) are run as
  separate statements — fine for plain SQL.
- Strings containing `;` get split mid-string and fail with `Parser Error: unterminated quoted string`. This breaks JSX/TSX or any payload with embedded semicolons.
- Single-quote escaping (`''`) is NOT enough — the splitter operates before
  the SQL parser, so it doesn't honour string boundaries.

**Workaround for non-SQL payloads (JSX, JSON, code blobs):** base64-encode the
payload and decode in SQL:

```python
import base64
payload = open("dive.tsx").read()
b64 = base64.b64encode(payload.encode("utf-8")).decode("ascii")
query = f"SELECT * FROM MD_CREATE_DIVE(title='X', content=decode(from_base64('{b64}')))"
```

`decode(...)` defaults to UTF-8. The base64 alphabet `[A-Za-z0-9+/=]` contains
no `;`, no `'`, and no newlines, so the splitter passes it through unscathed.

This same trick works for any DuckDB function that accepts a VARCHAR — not
just MotherDuck Dive functions.

## Diagnosing failures

The `externalMessage` field on a failed task run is the verbatim error from
the underlying integration (e.g. DuckDB / MotherDuck). Read it carefully —
it's almost always exact about the offending column / line. The `taskParameters.query` field shows the rendered SQL (after Orchestra's
templating, but before `;`-splitting), which is invaluable for diagnosing the
two gotchas above.

## When to prefer GitHub-backed import

Use `mcp__orchestra__import_pipeline` (which reads from a GitHub repo) when:
- The pipeline is part of a reviewed change in a Git workflow,
- You want the pipeline tied to a specific commit/branch,
- You don't want to embed an API key in a script.

Use the public REST API direct path (this skill) when:
- Iterating on shape/parameters fast,
- Generating pipelines programmatically,
- Working in an unpushed local branch.

## See also

- `references/cookbook.md` — copy-pasteable Python snippets for create / update
  / start / poll, plus the base64 helper.
- The `motherduck-dive-publishing` skill for end-to-end Dive shipping that
  uses every gotcha here.
