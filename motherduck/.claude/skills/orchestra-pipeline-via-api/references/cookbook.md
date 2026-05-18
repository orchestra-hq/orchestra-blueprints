# Orchestra pipeline cookbook

Copy-pasteable snippets. **Prefer the MCP path first.** REST is the fallback
when MCP tools aren't surfaced.

## MCP-first path (preferred)

```python
# Validate
mcp__orchestra__validate_pipeline pipeline_definition=<dict>
# → {"message": "Pipeline schema is valid"}

# Create (first time)
mcp__orchestra__create_pipeline alias="my_alias" data=<dict> published=True

# Update (every iteration after that)
mcp__orchestra__update_pipeline alias="my_alias" data=<dict> published=True

# List all pipelines for the workspace
mcp__orchestra__list_pipelines

# Trigger a run
mcp__orchestra__start_pipeline alias_or_pipeline_id="my_alias" run_inputs={...}

# Check status
mcp__orchestra__get_pipeline_run_status pipeline_run_id="<id>"

# Diagnose
mcp__orchestra__list_task_runs pipeline_ids="<id>" time_from="..." time_to="..."
```

If `validate_pipeline` / `create_pipeline` / `update_pipeline` aren't in your
tool registry: `ToolSearch +orchestra +pipeline`. If they're still missing,
the MCP server may need a restart — only then fall back to REST.

## REST fallback

Assumes `ORCHESTRA_API_KEY` is in `~/.claude/mcp.json`
(`mcpServers.orchestra.env.ORCHESTRA_API_KEY`) — the same key the Orchestra
MCP uses.

## Helper: read API key

```python
import json
key = json.load(open("/Users/<you>/.claude/mcp.json"))["mcpServers"]["orchestra"]["env"]["ORCHESTRA_API_KEY"]
```

## Validate a pipeline schema

```python
# Body is the pipeline `data` object directly — not wrapped in {"data": ...}.
import json, urllib.request
data = {...your pipeline def...}
req = urllib.request.Request(
    "https://app.getorchestra.io/api/engine/public/pipelines/schema",
    data=json.dumps(data).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
print(urllib.request.urlopen(req).read().decode())
# → {"message":"Pipeline schema is valid"}
```

If your local Python lacks SSL cert chain (Mac framework Python often does),
shell out to `curl` instead:

```bash
curl -sS -X POST https://app.getorchestra.io/api/engine/public/pipelines/schema \
  -H "Content-Type: application/json" -d @/tmp/data.json
```

## Create a pipeline (first time)

```bash
curl -sS -X POST https://app.getorchestra.io/api/engine/public/pipelines \
  -H "Authorization: Bearer $ORCHESTRA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"alias":"my_alias","published":true,"storage_provider":"ORCHESTRA","data":{...}}'
```

Returns `{"id":"...","alias":"my_alias","latestVersionNumber":1,...}`.

## Update an existing pipeline (every iteration after that)

```bash
curl -sS -X PUT https://app.getorchestra.io/api/engine/public/pipelines/my_alias \
  -H "Authorization: Bearer $ORCHESTRA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"data":{...},"published":true}'
```

Bumps `latestVersionNumber`.

## YAML → JSON converter

```python
import yaml, json
d = yaml.safe_load(open("pipelines/my.yaml").read())
open("/tmp/data.json","w").write(json.dumps(d))
open("/tmp/upsert.json","w").write(json.dumps({"data": d, "published": True}))
```

## base64 a payload for embedding inside SQL

Use this whenever Orchestra's split-on-`;` would mangle a multi-line / JSX /
code blob inside `parameters.query`. Pair with `decode(from_base64('<b64>'))`
in DuckDB.

```python
import base64
payload = open("dives/my-dive/my-dive.tsx").read()
b64 = base64.b64encode(payload.encode("utf-8")).decode("ascii")
query = (
    "SELECT * FROM MD_CREATE_DIVE("
    f"title='My Dive', "
    f"content=decode(from_base64('{b64}'))"
    ")"
)
```

## Trigger a run (prefer MCP)

```python
# Via Orchestra MCP — preferred from inside Claude Code:
# mcp__orchestra__start_pipeline alias_or_pipeline_id="my_alias" run_inputs={...}

# Direct REST (note camelCase `runInputs` here vs MCP's `run_inputs`):
import json, urllib.request
req = urllib.request.Request(
    "https://app.getorchestra.io/api/engine/public/pipelines/my_alias/start",
    data=json.dumps({"runInputs": {"foo": "bar"}}).encode(),
    headers={
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    },
    method="POST",
)
print(urllib.request.urlopen(req).read().decode())
# → {"pipelineRunId":"...","message":"Pipeline run created successfully"}
```

## Poll a run

```python
# mcp__orchestra__get_pipeline_run_status pipeline_run_id="..."
# Returns {"id","pipeline_id","pipeline_name","run_status"} where run_status ∈
#   {CREATED, RUNNING, SUCCEEDED, WARNING, FAILED, CANCELLING, CANCELLED}.
```

For the verbatim error from a failed task, use
`mcp__orchestra__list_task_runs` filtered by `pipeline_ids=<id>` and a tight
time window. The `externalMessage` field is the underlying integration's
verbatim error.

## Common task-run filter pitfalls

- `time_from` and `time_to` must be ≤168h apart (1 week max window).
- `status` filter rejects values not in the documented enum (e.g. lowercase
  fails). Default to omitting the filter.
- `integration` rejects unknown integrations (e.g. `MOTHER_DUCK` fails;
  `MOTHERDUCK` is correct).
- For large responses, the tool may overflow its token limit and save to a
  file — use `jq` to pull just what you need.

## Anti-patterns we've hit

- **Triggering before the PUT lands**: when iterating fast, make sure the
  `PUT` returned the bumped `latestVersionNumber` before calling
  `start_pipeline`, otherwise the run uses the previous version.
- **Trusting the docs example for templating**: the docs show `${{ inputs.x }}`
  embedded in a longer parameter value as if it works. It doesn't (in current
  Orchestra). Hardcode embedded values, or generate the YAML from a script.
- **Putting `;` inside parameter strings**: any payload with `;` (TSX, JSON,
  code) breaks Orchestra's pre-parser splitter. base64 it.
- **Mixing snake_case / camelCase between MCP and REST**: MCP uses
  `run_inputs` (snake_case), REST uses `runInputs` (camelCase). Easy to confuse.
