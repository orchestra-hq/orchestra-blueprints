# Dive design notes

Distilled from the upstream `motherduck-create-dive` SKILL and the practical
lessons of shipping `Orchestra Admin: Top Failing Pipelines (7d)`.

## Component contract

- React + `@motherduck/react-sql-query`, default export.
- Backticked SQL inside `useSQLQuery` — fully qualified table names
  (`db.schema.table`).
- Per-query loading / empty / error states (don't share one boundary across
  multiple queries — they refresh independently).
- Convert SQL values defensively: a small helper like `const N = (v: unknown): number => v != null ? Number(v) : 0` saves you when DuckDB returns `BIGINT` as a string in JS.
- Supported runtime libraries: `react`, `@motherduck/react-sql-query`,
  `recharts`, `lucide-react`. Verify with `get_dive_guide` (MCP) before
  pulling in something newer.

## Multi-query Dives

Use multiple `useSQLQuery` calls. Name destructures uniquely
(`{ data: kpiData, isLoading: kpiLoading } = useSQLQuery(...)`). Each section
renders its own loading/error state.

Prefer one query per visual section over one mega-query that's reshaped in
React. SQL is the right place to do reshaping; React is the right place to do
presentation.

## Theming

Pick a named theme rather than a vague vibe ("Corporate Dashboard", "FT
Salmon", "Tufte Minimal"). Specify palette roles, chart density, layout
intent, and interactivity expectations. Restraint > ornamentation; a quiet
KPI label and a thin line beats a heavy card with a shadow.

## Required resources

If the Dive queries data outside the user's home database (e.g. a share),
declare it.

Local-preview export (single line — the deploy script regex requires it):

```tsx
export const REQUIRED_DATABASES = [{ type: "share", path: "md:_share/<owner>/<uuid>", alias: "shared_alias" }];
```

Server-side: pass `required_resources` to `MD_CREATE_DIVE` /
`MD_UPDATE_DIVE_CONTENT`, or set it in `dive_metadata.json` if you're using
the Dives-as-code blessed-repo pattern.

Avoid aliases that collide with existing user databases. Suffix with `_share`
when in doubt.

## Layout patterns that work

- **One KPI row + one primary chart + one supporting table** is the
  workhorse layout. Everything else is harder to read at a glance.
- For ranking, use a horizontal bar chart sorted by the metric.
- For trends, use a line chart with a series per dimension (cap to 5 series;
  add a small-multiples view if more).
- For drill-down, render a table.

## Loading / empty / error states

Always provide all three:
- Loading: skeleton or `"Loading..."` — must be visible immediately.
- Empty: positive framing ("No failures in the last 7 days." not "No data").
- Error: surface `error.message` so the user can debug.

Do NOT swallow `isError` — render *something* the user can act on.

## Common pitfalls

- Letting `REQUIRED_DATABASES` diverge from `dive_metadata.json.requiredResources` — they must mirror.
- Multi-line `REQUIRED_DATABASES` — breaks the deploy script regex.
- Shadowing a destructured name across two `useSQLQuery` calls — silent bug.
- Forgetting that `value` from DuckDB is sometimes `bigint` serialized as
  string in JS — wrap with `Number(...)`.
- Putting `;` in any payload that goes through Orchestra's
  MOTHERDUCK_EXECUTE_QUERY without base64 encoding.
- Trying to publish markdown as a Dive. Markdown isn't a Dive; React TSX is.

## Relationship to Dives-as-code

The blessed example repo (`motherduckdb/blessed-dives-example`) wraps this
flow with:

```text
dives/<name>/<name>.tsx
dives/<name>/dive_metadata.json
.dive-preview/src/dive.tsx        # local preview Vite scaffold
scripts/deploy-dive.sh
.github/workflows/deploy_dives.yaml
.github/workflows/cleanup_preview_dives.yaml
```

If the project grows beyond a single Dive, migrate to this layout. For one or
two Dives shipped via Orchestra, the simpler pattern in this repo
(`dives/<name>/<name>.tsx` + base64 in pipeline YAML) is enough.
