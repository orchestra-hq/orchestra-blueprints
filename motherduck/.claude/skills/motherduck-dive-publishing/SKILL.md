---
name: motherduck-dive-publishing
description: Publish, update, and version MotherDuck Dives (live React + SQL data apps) programmatically via the MD_*_DIVE SQL functions. Use this when the user wants to ship a Dive without using the MotherDuck UI or MCP tools — i.e. via Orchestra MOTHERDUCK_EXECUTE_QUERY, a Python DuckDB session, dbt, or any other SQL surface that can talk to MotherDuck. Also use when authoring the React TSX content for a Dive, navigating the difference between MD_CREATE_DIVE and MD_UPDATE_DIVE_CONTENT (different return columns!), or working around the Orchestra split-on-semicolon issue when shipping TSX.
---

# Publishing MotherDuck Dives via SQL

A MotherDuck Dive is a live React + SQL component saved in MotherDuck. It
queries MotherDuck via `useSQLQuery` and renders an interactive UI. Dives are
manageable via SQL table functions, which means you can ship one from any
SQL-speaking surface — including Orchestra MOTHERDUCK_EXECUTE_QUERY, a plain
DuckDB Python session, dbt, etc. No MCP required.

## When to reach for this

- The user wants the answer to an analytics question to be a Dive (not just a
  markdown blob from an LLM).
- The user is iterating on a Dive's content from disk (TSX file in the repo)
  and wants every refresh to ship the latest version.
- The user is automating Dive maintenance from a pipeline (Orchestra, dbt,
  Airflow…) without depending on Claude Code's MotherDuck MCP being connected.

If the user just wants to *create* a Dive interactively in a chat session and
MotherDuck MCP is connected, prefer the MCP `create_dive` tool — it's
ergonomic and previews locally.

## The Dive SQL functions

| Function | Purpose | Required args | Notable returned columns |
| -------- | ------- | ------------- | ------------------------ |
| `MD_CREATE_DIVE` | Create a new Dive | `title`, `content` | `id` (Dive UUID), `current_version` (1), `version_id`, `version_storage_url`, `version_created_at`, `version_api_version`, `version_required_resources` |
| `MD_UPDATE_DIVE_CONTENT` | Push new content; bumps version | `id`, `content` | `id` (= the version's ID, NOT the dive's), `version` (new version number), `api_version`, `description`, `required_resources` |
| `MD_UPDATE_DIVE_METADATA` | Change title / description without bumping content version | `id`, plus optional `title`, `description` | metadata fields |
| `MD_LIST_DIVES` | Paginated Dive listing | none | dive metadata |
| `MD_GET_DIVE` | Read current Dive content | `id` | full content + metadata |
| `MD_LIST_DIVE_VERSIONS` / `MD_GET_DIVE_VERSION` | Version inspection | `id` (+ `version`) | per-version content / metadata |
| `MD_DELETE_DIVE` | Permanent delete | `id` | — destructive; confirm before using. |

**Critical**: `MD_CREATE_DIVE` and `MD_UPDATE_DIVE_CONTENT` return DIFFERENT
column names. If you blindly `SELECT id, version, created_at` from create and
the same from update you will hit `Binder Error: Referenced column "version"
not found in FROM clause` on update. Always `SELECT *` first when you're new
to a function, then narrow once you've seen the schema.

Optional named args supported by create/update (consult docs for current
list): `description` (varchar), `api_version` (uinteger). Create also accepts
`required_resources` (array of share/database refs).

## Anatomy of a Dive component

The `content` field is React TSX (not markdown — markdown is *not* a Dive).
Minimum shape:

```tsx
import { useSQLQuery } from "@motherduck/react-sql-query";

const N = (v: unknown): number => (v != null ? Number(v) : 0);

export default function MyDive() {
  const { data, isLoading, isError, error } = useSQLQuery(`
    SELECT month, SUM(revenue) AS revenue
    FROM "my_db"."analytics"."orders"
    GROUP BY 1 ORDER BY 1
  `);
  const rows = Array.isArray(data) ? data : [];

  if (isError) return <div>Failed to load: {error?.message}</div>;
  return <div>{isLoading ? "Loading..." : rows.map(r => N(r.revenue)).join(", ")}</div>;
}
```

Supported runtime libraries: React, `@motherduck/react-sql-query`, Recharts,
`lucide-react`. No browser-side secrets. Multi-section Dives use multiple
`useSQLQuery` calls with uniquely named destructures and per-section
loading/empty/error states.

If a Dive needs a shared/external database, declare it via
`REQUIRED_DATABASES` (local preview) or `required_resources` (saved Dive). The
local-preview export must be on a single line — Orchestra's blessed deploy
script strips it via regex.

## Shipping the TSX (the gotcha that wastes the most time)

Orchestra's MOTHERDUCK_EXECUTE_QUERY task hard-splits the `query` parameter on
`;` before sending to DuckDB. TSX/JSX has many `;` characters. You will hit
`Parser Error: unterminated quoted string` even when single-quote escaping is
perfect.

**Fix: base64 the TSX, decode in SQL.** base64's alphabet
(`[A-Za-z0-9+/=]`) is `;`-free, `'`-free, and newline-free, so it survives
both Orchestra's splitter and DuckDB's parser:

```python
import base64
tsx = open("dives/my-dive/my-dive.tsx").read()
b64 = base64.b64encode(tsx.encode("utf-8")).decode("ascii")
title = "My Dive"
query = (
    "SELECT * FROM MD_CREATE_DIVE("
    f"title='{title}', "
    f"content=decode(from_base64('{b64}'))"
    ")"
)
```

DuckDB's `decode(blob, 'utf-8')` defaults to UTF-8 when called as `decode(blob)`.

Use this same pattern for `MD_UPDATE_DIVE_CONTENT(id='...'::UUID, content=decode(from_base64('...')))`.

This trick generalises to any DuckDB function that takes VARCHAR but where
your payload contains `;`.

## Orchestra-specific: the publish-dive task pattern

Combine the publish step into your main pipeline as the terminal task. It
should depend on every mart-build task so it only runs once data is fresh.

```yaml
publish-dive:
  integration: MOTHERDUCK
  integration_job: MOTHERDUCK_EXECUTE_QUERY
  connection: ${{ inputs.motherduck_connection_id }}
  name: Republish MotherDuck Dive
  depends_on: [build-dim-pipeline, build-fct-pipeline-run, ...]
  parameters:
    set_outputs: true
    query: |
      SELECT id, version, api_version
      FROM MD_UPDATE_DIVE_CONTENT(
        id='<dive-uuid>'::UUID,
        content=decode(from_base64('<base64-of-tsx>'))
      )
```

Hardcode the Dive UUID and the base64 in the YAML (see the
`orchestra-pipeline-via-api` skill for why embedded `${{ inputs.x }}` doesn't
substitute). Refresh the YAML from a Python script that reads the TSX and
re-encodes the base64 before each `PUT /pipelines/{alias}`.

## Lifecycle pattern

1. **First-time create** — call `MD_CREATE_DIVE` once. Save the returned `id`
   (the Dive UUID) somewhere durable: `README.md`, a config file, or a
   pipeline input default. Don't re-run create — that makes a *new* Dive.
2. **Subsequent updates** — call `MD_UPDATE_DIVE_CONTENT(id=<saved-id>::UUID, content=...)`.
   This bumps the version. The Dive in the UI updates atomically.
3. **Reading current state** — `MD_GET_DIVE(<id>)` or `MD_LIST_DIVES()`. Use
   when you need to confirm the Dive exists / find an existing one by title.
4. **Renames** — `MD_UPDATE_DIVE_METADATA` (does NOT create a content version).

## Layout patterns

For a single Dive shipped via Orchestra, `dives/<name>/<name>.tsx` plus base64
in the pipeline YAML is enough. See `references/dive_design_notes.md` when the
project grows beyond that.

## See also

- `references/dive_design_notes.md` — design principles, multi-query layout,
  REQUIRED_DATABASES, theming.
- `orchestra-pipeline-via-api` skill — for the Orchestra-side mechanics.
- Upstream MotherDuck SKILL: <https://github.com/motherduckdb/agent-skills>.
