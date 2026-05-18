---
name: publish-motherduck-dive
description: Publish or update a MotherDuck Dive by inlining a local .tsx file into a `MD_CREATE_DIVE` / `MD_UPDATE_DIVE` SQL call sent through the MotherDuck MCP (`mcp__MotherDuck__query_rw`). Use this when the user says "publish the dive", "ship this dive to MotherDuck", or "update dive <id>". Reads the TSX from `.dive-preview/src/dive.tsx` (override-able), SQL-escapes it, executes via MCP, and records the returned dive UUID in `.dive-preview/dive_id.txt`.
---

# Publish a MotherDuck Dive from a local TSX file

The Dive UI source lives in `.dive-preview/src/dive.tsx`. Publishing means inlining
that file's contents into a `SELECT * FROM MD_CREATE_DIVE(title=..., content=...)`
call (or `MD_UPDATE_DIVE` for an existing dive) and running it against MotherDuck.

The shape of the call:

```sql
SELECT * FROM MD_CREATE_DIVE(
  title   = 'PokeDuck',
  content = '
    import { useSQLQuery } from "@motherduck/react-sql-query";
    export default function Dive() {
      const { data } = useSQLQuery(
        `SELECT PROMPT(''Suggest a duck type or pokemon and tell a fun fact about them'')`,
        { select: (rows) => Object.values(rows[0])[0] }
      );
      return <div><p>FUN FACT:</p><p>{JSON.stringify(data)}</p></div>;
    }'
);
```

Two things to notice: the entire TSX sits inside a single-quoted SQL string, and
every single quote inside the TSX is doubled (`'` → `''`). That escape is the
only transformation between the file on disk and the SQL payload.

## Inputs

- **TSX path** — default `.dive-preview/src/dive.tsx`. If the user names a different
  file, use that.
- **Title** — required for create, optional for update. If the user doesn't supply
  one, ask. Don't invent a title from the file contents.
- **Dive ID** — required for update only. UUID. If the user says "update the dive"
  without an ID, check `.dive-preview/dive_id.txt` for the most recent entry and
  confirm with the user before using it.
- **Description** — optional, both create and update.

## Steps

### 1. Read the TSX, substitute placeholders, then SQL-escape

Read the source file (Read tool), substitute publish-time placeholders, then
double every single quote. Do everything in memory — don't write an intermediate
`.sqlesc` file. (The existing `.dive-preview/sql_escape.py` and
`.dive-preview/dive.tsx.sqlesc` are leftovers from an earlier workflow; ignore
them.)

**Publish-time placeholders**

The TSX may declare top-level constants whose values are sentinel strings the
skill replaces at publish time. These act as build-time "env vars" inside the
TSX — hard-coded by default so the file still compiles in the local Vite
preview, then overwritten by the skill just before the dive is sent to
MotherDuck:

| Sentinel               | Replaced with                                                                 |
| ---------------------- | ----------------------------------------------------------------------------- |
| `__LAST_UPDATED_AT__`  | ISO timestamp of "now" at publish time (UTC, second precision).               |
| `__ORCHESTRA_RUN_URL__`| `https://app.getorchestra.io/pipeline-runs/<run-uuid>/lineage` for the latest succeeded run of the pipeline that backs this dive. |

The TSX is expected to reference these via constants whose initial value is the
sentinel itself, e.g.:

```tsx
const LAST_UPDATED_AT = "__LAST_UPDATED_AT__";
const ORCHESTRA_RUN_URL = "__ORCHESTRA_RUN_URL__";
```

The dive's JSX should guard against the un-substituted sentinel so the file
still renders cleanly in the local preview (e.g. show `"—"` and hide the link).
That's a dive-file concern, not a skill concern — don't try to enforce it from
here.

To resolve `__ORCHESTRA_RUN_URL__`:

1. Ask the user which Orchestra pipeline backs this dive (or read it from a
   sidecar config if one exists). Don't guess — pipeline UUIDs are not
   recoverable from the dive content.
2. `mcp__orchestramcp__list_pipeline_runs(pipeline_id="<uuid>")`.
3. Take the most recent run with status `SUCCEEDED`. If none, surface the issue
   and ask the user how to proceed — don't silently link a `FAILED` run.
4. Build `https://app.getorchestra.io/pipeline-runs/<run-uuid>/lineage`.

If the TSX doesn't contain a sentinel, skip the substitution and the
Orchestra lookup for that one — only do the work the file actually opts into.

**The substitution + escape**

```python
import datetime
content = open(tsx_path, encoding="utf-8").read()
content = content.replace("__LAST_UPDATED_AT__",
                          datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S UTC"))
content = content.replace("__ORCHESTRA_RUN_URL__", run_url)
escaped = content.replace("'", "''")
```

Substitute **before** escape — otherwise an apostrophe in the substituted value
gets through un-doubled. That's the only escape needed for SQL: backslashes,
newlines, and template-literal backticks all pass through `MD_CREATE_DIVE`'s
string literal unchanged.

### 2. Build the SQL

For a new dive:

```sql
SELECT * FROM MD_CREATE_DIVE(
  title   = '<title>',
  content = '<escaped tsx>'
);
```

For an update:

```sql
SELECT * FROM MD_UPDATE_DIVE(
  id      = '<dive-uuid>',
  title   = '<title>',
  content = '<escaped tsx>'
);
```

Escape single quotes in the title the same way (`'` → `''`). Description, if
provided, is an extra `description = '...'` argument on either function.

### 3. Execute via the MotherDuck MCP

**Always send the SQL through `mcp__MotherDuck__query_rw`.** Don't reach for a
local `duckdb` install, raw HTTP, or anything else — the MCP is the supported
path and `MOTHERDUCK_API_TOKEN` is already wired into it from the environment.

```
mcp__MotherDuck__query_rw(sql="<the SQL from step 2>")
```

`query_rw` (not `query`) because `MD_CREATE_DIVE` / `MD_UPDATE_DIVE` write state.
You don't need a `database` argument — these are account-level calls.

The SQL string is large (the whole TSX file plus the wrapper — often 5–15 KB).
The practical way to assemble it for the MCP call:

1. Use a one-shot Python helper (write it as `.dive-preview/_build_publish_sql.py`
   to keep PowerShell quoting out of play) that reads the TSX, substitutes the
   publish-time placeholders, escapes, and writes the full SQL to a temp file:

   ```python
   # .dive-preview/_build_publish_sql.py
   import datetime, os, pathlib, sys

   title = sys.argv[1]
   run_url = os.environ.get("ORCHESTRA_RUN_URL", "")
   tsx = pathlib.Path(".dive-preview/src/dive.tsx").read_text(encoding="utf-8")

   tsx = tsx.replace(
       "__LAST_UPDATED_AT__",
       datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
   )
   if run_url:
       tsx = tsx.replace("__ORCHESTRA_RUN_URL__", run_url)

   title_esc   = title.replace("'", "''")
   content_esc = tsx.replace("'", "''")
   sql = (
       "SELECT * FROM MD_CREATE_DIVE(\n"
       f"  title   = '{title_esc}',\n"
       f"  content = '{content_esc}'\n"
       ");\n"
   )
   pathlib.Path(".dive-preview/_publish.sql").write_text(sql, encoding="utf-8")
   ```

   Invoke with the title as argv and the run URL via env var:

   ```powershell
   $env:ORCHESTRA_RUN_URL = 'https://app.getorchestra.io/pipeline-runs/<run-uuid>/lineage'
   python .dive-preview\_build_publish_sql.py "Linear issues v3"
   ```

2. Read `.dive-preview/_publish.sql` with the Read tool.
3. Pass the file's contents as the `sql` argument to `mcp__MotherDuck__query_rw`.
4. Delete `.dive-preview/_publish.sql` and `.dive-preview/_build_publish_sql.py`
   after the call succeeds — both are build artifacts, not source.

For updates, swap `MD_CREATE_DIVE(title=..., content=...)` for
`MD_UPDATE_DIVE(id='<uuid>', title=..., content=...)` in the Python snippet.

**Why not `mcp__MotherDuck__save_dive` / `update_dive`?** Those MCP tools exist
and would work without the escape-and-inline dance, but the user explicitly chose
the SQL pattern so the source of truth is the file on disk plus a SQL string you
can paste anywhere. Stick with `MD_CREATE_DIVE` / `MD_UPDATE_DIVE` via
`query_rw` unless the user asks otherwise.

### 4. Record the dive ID

The returned row contains the dive's UUID (and usually a `url` or `share_url`).
Append a line to `.dive-preview/dive_id.txt` so future runs can find it:

```
<UUID>  -  <title>   (created <YYYY-MM-DD>)
```

For an update, add a new line rather than mutating the existing entry — the file
is a publish log, not the current state. If `.dive-preview/dive_id.txt` doesn't
exist, create it.

Surface the dive URL back to the user as the final message.

## Notes

- **Don't read the token from `.dive-preview/.env`.** That file is for the local
  Vite preview server. The MCP picks up `MOTHERDUCK_API_TOKEN` from the process
  env on its own — never echo, copy, or paste the token value into chat or a file.
- **Don't run `npm run build` or bundle the TSX first.** `MD_CREATE_DIVE` accepts
  the raw TSX source; MotherDuck compiles it server-side. Bundling defeats the
  point of editing in `.dive-preview/src/dive.tsx`.
- **If the SQL fails with a parse error**, it's almost always an unescaped `'`
  somewhere in the TSX. Re-check that the in-memory `replace("'", "''")` ran on
  the exact bytes you sent — a stale `.sqlesc` file is the classic foot-gun.
- **`.dive-preview/dive.tsx.b64`** is from an older base64-encoded publish flow.
  Don't use it; it's kept as a reference for the v1→v2 migration noted in
  `dive_id.txt`.
- See `orchestra-pipeline` if the user wants to schedule the publish (wrap the
  SQL in a `MOTHERDUCK_EXECUTE_QUERY` task).
