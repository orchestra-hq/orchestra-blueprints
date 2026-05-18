---
name: motherduck-orchestra-analysis
description: End-to-end Orchestra metadata analytics in MotherDuck — profile live source data, extend the user's existing Orchestra pipeline (ingest already present) with mart SQL tasks appended downstream, validate and run until green, then author and verify a MotherDuck Dive that answers the question. Use when the user asks an analytics question about Orchestra metadata (slowest/failing pipelines, run health, durations, integrations, assets, etc.), mentions a Dive, or says work should go into a named pipeline, alias, ID, or Orchestra URL. Do not read checked-in sql/*.sql as the mart spec. Optional stop after marts when the user only wants pipeline work.
---

# Orchestra metadata question → marts → Dive

MCP first: Orchestra MCP, Orchestra Docs MCP, MotherDuck MCP — before REST or local scripts.

## What the user gives you

| Input | Required | Notes |
| ----- | -------- | ----- |
| Analytics question | Yes | Quote it in dive drafts and the Dive title. |
| Target Orchestra pipeline | Yes | Alias, UUID, or `https://app.getorchestra.io/...` URL. **No default pipeline** in this repo. |
| Stop after marts | No | Skip Dive steps when the user only wants mart tasks deployed and passing. |

The named pipeline **already includes ingest** (or equivalent upstream load). Do not author, copy, or regenerate ingest tasks. All new work is **appended downstream**.

### Natural-language signals

Treat these as **extend this pipeline** (skip "new vs extend?" unless the target is missing):

- "ingesting … in this pipeline"
- "add … into it" / "append" / "wire into" / "tack onto"
- A pipeline URL, alias, or ID in the same message as the question

Example:

> Let's dive into my slowest Orchestra pipelines. I'm ingesting the metadata in this pipeline, so add any work for the full analysis into it: `https://app.getorchestra.io/pipelines/…`

## Workflow

### 1. Resolve the pipeline

1. Parse alias or ID from a URL when given.
2. `mcp__orchestra__list_pipelines` (and local `pipelines/*.yaml` if present) to load task groups, `depends_on`, and the last upstream group before mart work attaches.
3. Ask only if the question or pipeline target is missing or ambiguous.

### 2. Profile live source data and design marts

Do **not** treat `sql/*.sql` as the source of truth. Introspect MotherDuck:

- Inventory databases, schemas, tables, columns; sample rows and time windows.
- Infer grains, keys, and measures needed to answer the question.
- Propose facts/dims; confirm with the user when the model is non-obvious.

Use `motherduck-marts-pipeline` plus `references/profile_checklist.md` (in that skill) for depth and SQL patterns.

### 3. Author SQL and extend the pipeline

- Write `sql/<alias>.sql` and keep `pipelines/<alias>.yaml` in sync with what you deploy (including upstream tasks you did not change).
- **Append, never replace** existing task groups. New mart groups `depends_on` the appropriate upstream group (usually the ingest/load group).
- If `publish-dive` already exists, insert new build groups **before** it and add the new group to `publish-dive.depends_on`.

Details: `motherduck-marts-pipeline`, `orchestra-pipeline-via-api`.

### 4. Validate, deploy, iterate

1. `mcp__orchestra__validate_pipeline`
2. Deploy via Orchestra MCP or REST PUT (`references/workflow_rules.md`)
3. `mcp__orchestra__start_pipeline` → `mcp__orchestra__get_pipeline_run_status`
4. Spot-check mart tables (row counts, freshness, sanity SQL aligned with the question)

On failure, fix SQL or dependencies and repeat until the run succeeds.

**Stop here** when the user asked for marts only.

### 5. Answer with a MotherDuck Dive

Follow `motherduck-dive-from-question`:

- Interrogate marts; write `dive_drafts/answer_<slug>.txt` and `dive_drafts/dive_plan_<slug>.md`.
- Author TSX under `dives/<slug>/`; publish via `motherduck-dive-publishing`.

### 6. Verify the Dive

Queries run, layout matches the plan, headline numbers match mart SQL. Fix and republish if not.

### 7. Ask about Dive republish in the pipeline

After verification, ask whether future runs should include a `publish-dive` (or similar) task. Do not add republish tasks without explicit approval.

## Definition of done

- Marts required for the question exist in MotherDuck and were built by a successful run of the user's pipeline (extended, not replaced).
- Unless **stop after marts**: published Dive verified; user prompted on pipeline wiring for republish.
- Reply with run ID, mart spot-checks, and Dive link or UUID when a Dive shipped.

## See also

- `references/workflow_rules.md` — append-only extension, introspection, templating, Orchestra PUT gotchas.
- `references/example_invocations.md` — copy-paste user phrasing.
- `motherduck-marts-pipeline` — mart SQL and Orchestra task shape.
- `motherduck-dive-from-question` — Dive authoring, verify, optional wiring.
- `motherduck-dive-publishing` — base64, `MD_*_DIVE` mechanics.
- `orchestra-pipeline-via-api` — REST fallback and large YAML.
