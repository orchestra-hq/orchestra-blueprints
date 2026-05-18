---
name: motherduck-dive-from-question
description: Step 2 of the MotherDuck-on-Orchestra workflow. Take a user analytics question, interrogate marts in MotherDuck for a direct text answer and dive plan, then author a React TSX Dive and publish or republish via MD_CREATE_DIVE / MD_UPDATE_DIVE_CONTENT. Use when the user asks a question of their data and wants a shareable live-querying Dive, or when motherduck-orchestra-analysis reaches the Dive phase. Handles first-time creation (dives/<slug>/.dive_id), republishes, verification, and always asks whether to wire republish into the pipeline that rebuilds marts. Pair with motherduck-marts-pipeline for Step 1 and motherduck-orchestra-analysis for the full flow.
---

# Analytics question → MotherDuck Dive

This is Step 2 of the two-step MotherDuck-on-Orchestra workflow:

1. Step 1 — `motherduck-marts-pipeline`: durable infra (marts + Orchestra
   pipeline).
2. **Step 2 (this skill)** — per-question artefact (text answer + published
   Dive).

`motherduck-orchestra-analysis` runs Step 1 then Step 2 in one user message
unless the user stops after marts.

A Dive is a live React + SQL component saved in MotherDuck. The TSX runs
`useSQLQuery` hooks against the marts every time someone opens the Dive, so
the answer stays fresh as long as Step 1 keeps rebuilding the marts.

## When to invoke

- "What are the top failing pipelines in the last 30 days? Make me a Dive."
- "Build a Dive showing daily success rate by environment."
- "Update the Top Failing Pipelines Dive to show 90 days instead of 30."
- "Interrogate the marts and tell me which integration is flakiest, then
  publish a Dive on it."
- "Let's dive into my slowest Orchestra pipelines" (after or with Step 1 marts)

Skip if the user wants:
- A static answer with no Dive ("just tell me the top 5"). Just run the SQL
  via `mcp__MotherDuck__query` and reply.
- New mart tables — that's Step 1.
- Pure TSX edits without a question to answer — use `motherduck-dive-publishing`
  directly (the tactical skill underneath).

## Required context (ask if missing)

| Input | Default | Notes |
| ----- | ------- | ----- |
| The analytics question | — | Required. Quote the user's wording in the dive draft and the TSX header. |
| MotherDuck database + marts schema | look up via `mcp__MotherDuck__list_databases` if not in repo | E.g. `my_db.orchestra_marts`. |
| Existing Dive UUID (if updating) | `dives/<slug>/.dive_id` if present | Empty file / no dir → create new. |
| Target pipeline (for wiring) | from the user's message or Step 1 | Alias, ID, or URL of the pipeline that builds these marts. |
| Time window | 30 days | Use trailing windows (`NOW() - INTERVAL N DAY`) keyed on `started_at` for run-style facts. |

Pipeline-wiring is not required up front — ask at step 5 after verification.
Default the wiring target to the pipeline the user named for ingest or marts.

### 1. Understand the question — interrogate the marts

Use `mcp__MotherDuck__query` to answer the question directly first. Try
several angles:

- Headline numbers (totals, failure counts, distinct entities affected)
- Top-N breakdown (top failing pipelines, top integrations, etc.)
- Time trend if it's a "lately" question (daily/weekly rollup)
- One drill-down ("for the worst pipeline, which task fails most?")

Look at `mcp__MotherDuck__list_columns` for any mart you're about to query —
don't assume a column exists. The Dive will fail in production if you
hallucinate one.

Watch for case-mixed status enums; normalise with `UPPER(run_status) IN
('FAILED', 'ERROR')` rather than equality.

### 2. Write the dive draft to disk

Drop two artefacts in `dive_drafts/`:

- `dive_drafts/answer_<slug>.txt` — direct text answer the user asked for, in
  plain prose with the headline numbers. 5–10 lines max.
- `dive_drafts/dive_plan_<slug>.md` — the dive plan: title, layout sections
  (KPI strip, charts, tables), the SQL each section needs, columns/aggregations,
  recommended chart type per section.

These give the user something to react to before you spend tokens authoring
TSX. Show the plan and ask "ship this Dive as-is, or change anything?" — get
explicit confirmation for new Dives. (Skip the ask for republishes when the
user has already pinned the shape.)

### 3. Author the TSX

Drop at `dives/<slug>/<slug>.tsx`. The slug should be lowercase
snake-or-kebab — match what's in the repo if there's a convention.

Required shape (see `motherduck-dive-publishing` for the full anatomy):

```tsx
import { useSQLQuery } from "@motherduck/react-sql-query";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";

const N = (v: unknown): number => (v != null ? Number(v) : 0);

export default function <ComponentName>() {
  const headline = useSQLQuery(`
    SELECT
      COUNT(*) AS total_runs,
      SUM(CASE WHEN UPPER(run_status) IN ('FAILED','ERROR') THEN 1 ELSE 0 END) AS failed_runs
    FROM "my_db"."orchestra_marts"."fct_pipeline_run"
    WHERE started_at >= NOW() - INTERVAL 30 DAY
  `);
  // additional useSQLQuery calls per section
  // …
  const headlineRow = (Array.isArray(headline.data) ? headline.data : [])[0];

  return (
    <div className="p-6" style={{ background: "#f8f8f8", color: "#231f20" }}>
      <h1 className="text-2xl font-semibold">{/* question as title */}</h1>
      {/* KPI strip, chart, table — see existing dive for reference */}
    </div>
  );
}
```

Conventions for Dives in this workflow:

- Always wrap numerics in `N(...)` before render — DuckDB BIGINTs serialise as
  objects in JSX otherwise.
- Loading skeletons for every section (`isLoading ? <pulse-div/> : …`).
- Empty-state copy for sections that can come back empty.
- Brand palette: `#231f20` body text, `#6a6a6a` muted, `#bc1200` red,
  `#0777b3` blue, `#e5e5e5` borders. Stay consistent across sections.
- Trailing-30d windows on `started_at`. Make this consistent across all hooks
  in the Dive — mixing 30d and 7d in one Dive is a smell.

Each `useSQLQuery` gets a unique destructured name (`headline`, `topInt`,
`topPipelines`, `breakdown`). Don't reuse `data` across hooks.

If a Dive needs a shared/external database (rare in this workflow — marts
live in the user's own DB), set `REQUIRED_DATABASES` for local preview and
`required_resources` for publish.

### 4. Publish (first time vs republish)

The tactical mechanics live in `motherduck-dive-publishing`. The short
version:

**First time — `MD_CREATE_DIVE`:**

```sql
SELECT id, current_version, version_api_version
FROM MD_CREATE_DIVE(
  title='<Human title — usually the question>',
  content=decode(from_base64('<base64 of the TSX>'))
);
```

Run via `mcp__MotherDuck__query_rw`. The returned `id` (UUID) is the durable
handle to this Dive. Save it immediately:

```bash
echo '<uuid>' > dives/<slug>/.dive_id
```

Optionally add a short note to `README.md` for humans; `.dive_id` is the
durable handle.

**Subsequent — `MD_UPDATE_DIVE_CONTENT`:**

```sql
SELECT id, version, api_version
FROM MD_UPDATE_DIVE_CONTENT(
  id='<saved-uuid>'::UUID,
  content=decode(from_base64('<base64 of the TSX>'))
);
```

Different column names from create — always `SELECT *` first if you're new to
the function, otherwise you'll hit `Binder Error`.

**Why base64?** Both functions take a VARCHAR. If you embed TSX literally,
Orchestra (or any tool that splits on `;`) will mangle the payload. Base64
sidesteps it. See `motherduck-dive-publishing` for the encoder snippet.

### 5. Wire into an Orchestra pipeline (ASK every new Dive)

**Always ask** before finishing a new Dive: should the Dive refresh on every
run of an Orchestra pipeline that builds its marts? The target pipeline may
have been built by the Step 1 skill, extended by it, or pre-existed entirely
— it doesn't matter, as long as it rebuilds the marts the Dive queries.

Discover candidate pipelines:
- Local: `ls pipelines/*.yaml`.
- Orchestra: `mcp__orchestra__list_pipelines`.

Filter to pipelines whose `MOTHERDUCK_EXECUTE_QUERY` tasks reference the
schema/tables this Dive queries. If exactly one matches, default to it. If
several, list them in the prompt and let the user choose.

```
Question: "Wire <Dive title> into an Orchestra pipeline so it republishes on every rebuild?"
Header: "Wire to pipeline"
Options:
  - "Yes — add to <alias> (Recommended)"          ← one matching pipeline
      → patch pipelines/<alias>.yaml + Orchestra update_pipeline
  - "Yes — add to a different pipeline"           ← if multiple matched
      → list the others, pick one
  - "No — standalone Dive"
      → done; user republishes manually with MD_UPDATE_DIVE_CONTENT later
```

Default to "Yes" when at least one matching pipeline exists locally. The
whole point of the two-step flow is that mart rebuilds and Dive freshness
stay in lock-step — if a pipeline already maintains the marts, free
republishing is essentially free.

Skip this prompt on republishes (`.dive_id` already exists for the slug AND
the pipeline already has a `republish-*-dive` task for that UUID) — the
republish path just needs the base64 bumped in-place.

#### If yes: how to wire it

Patch the chosen pipeline (`pipelines/<alias>.yaml`). If a `publish-dive`
task group doesn't exist yet, create it:

```yaml
publish-dive:
  name: ''
  depends_on: [build-tables]
  tasks:
    republish-<slug>-dive:
      integration: MOTHERDUCK
      integration_job: MOTHERDUCK_EXECUTE_QUERY
      connection: ${{ inputs.motherduck_connection_id }}
      name: Republish <Dive title>
      depends_on: []
      parameters:
        set_outputs: true
        query: "SELECT id, version, api_version FROM MD_UPDATE_DIVE_CONTENT(id='<uuid>'::UUID, content=decode(from_base64('<b64>')))"
```

If `publish-dive` already exists on the target pipeline, add the new task as a
**sibling** under `publish-dive.tasks` — Orchestra runs sibling tasks in
parallel, which is what you want (each Dive republish is independent).

Task ID convention: `republish-<slug>-dive` where `<slug>` is the same kebab
slug used in `dives/<slug>/`. Task IDs must not collide with the group ID
(`publish-dive`) — see `orchestra-pipeline-via-api` for the full rule.

Deploy via `mcp__orchestra__update_pipeline` (MCP first). If the
`pipeline_definition` argument is >~20kb due to the base64 payload, fall back
to a Python helper that POSTs to `/api/engine/public/pipelines/{alias}` —
either is fine. **Don't** include `storage_provider` in the PUT body; it's
accepted on create only, and PUT rejects it as `extra_forbidden`.

On every TSX edit afterwards: re-base64, re-patch the YAML, re-PUT. The
pipeline alias stays the same; only the `query` field changes.

### 6. Verify

After publish:

- Confirm the Dive opens in the MotherDuck UI (give the user the URL pattern:
  `https://app.motherduck.com/dives/<uuid>`).
- `mcp__MotherDuck__query` a couple of the underlying SQL queries directly to
  sanity-check the numbers match what the Dive renders.
- If you wired Step 5, kick off the Orchestra pipeline once via
  `mcp__orchestra__start_pipeline` and watch the `republish-dive` task
  succeed.

### 7. Record the Dive handle

If a new Dive UUID was created, ensure `dives/<slug>/.dive_id` is saved.
Optionally note the UUID in `README.md` for humans.

Don't save memory entries for Dive UUIDs — `.dive_id` is the right home.

## Iterating on an existing Dive

Common path: user asks to change the window, add a section, swap a chart.

1. Edit the TSX in `dives/<slug>/<slug>.tsx`.
2. Re-base64 + `MD_UPDATE_DIVE_CONTENT` (or run the Orchestra pipeline if it
   has a `publish-dive` task).
3. Tell the user to reload the Dive — content is served live but the React
   bundle is cached per-session.

Skip the dive plan step on small edits. Re-run the plan + confirm dance if
you're adding a new section.

## Gotchas (cross-referenced)

| Gotcha | Where | Fix |
| ------ | ----- | --- |
| Orchestra splits MOTHERDUCK queries on `;` | TSX has many `;` | base64 the TSX, decode in SQL. |
| `MD_CREATE_DIVE` vs `MD_UPDATE_DIVE_CONTENT` return different columns | Reusing the same `SELECT id, version, ...` for both | `SELECT *` first; treat them as different functions. |
| BIGINT columns render as objects in JSX | KPI numbers come out as `[object Object]` | Wrap every numeric in `N()` helper before render. |
| Cancelling a pipeline run doesn't stop in-flight `MD_*_DIVE` | Cancelling create mid-flight | Wait for SQL; clean up the extra Dive with `MD_DELETE_DIVE` if needed. |
| Case-mixed status enums in source | Filters miss rows | `UPPER(status) IN ('FAILED','ERROR')` everywhere. |
| Stale upstream load | Trailing-30d window shows empty | Not a Dive bug — Step 1 marts are only as fresh as the upstream import. Tell the user. |

## See also

- `motherduck-dive-publishing` — wire-level Dive mechanics, function signatures,
  base64 encoder, lifecycle pattern, TSX anatomy.
- `motherduck-orchestra-analysis` — end-to-end question → marts → Dive.
- `motherduck-marts-pipeline` — Step 1 of this workflow.
- `orchestra-pipeline-via-api` — Orchestra mechanics for the optional Step 5
  pipeline-wired republish.
- `references/tsx_skeleton.md` — copy-pasteable TSX skeleton with KPI strip +
  chart + table sections.
- `references/dive_plan_template.md` — the dive plan structure to drop in
  `dive_drafts/`.
