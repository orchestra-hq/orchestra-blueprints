# Cleanup Plan

> Filled in by the Auditor agent. Specialist agents read their assigned section
> and only act on items tagged for their branch. Check items off as PRs land.

**Status:** 🟢 audit complete — awaiting review
**Auditor commit:** 61e6143
**Last updated:** 2026-05-12 10:41 UTC

---

## Connection IDs — not in scope

Orchestra connection IDs (e.g. `snowflake_12345`, connection names referenced
from `connection:` fields in pipeline YAMLs) are NOT considered secrets or
findings for this cleanup pass. Security agent: do not flag them. Pipelines
agent: do not rewrite them. They are opaque references, not credentials.

---

## Scope freeze

This cleanup pass does NOT include: adding new blueprints, changing pipeline
runtime behaviour, migrating between Orchestra schema versions, refactoring
dbt models, or touching connection IDs. Findings in those categories go to
"Cross-cutting follow-ups" for later work unless explicitly moved into the
"Pipeline lifecycle cleanup" section below.

---

## How to read this file

Each finding is one checkbox line:

`- [ ] <tag> <file:line> — <finding> — <suggested fix> — <branch>`

Tags: `structure | pipelines | python | dbt | security | docs | ci | deps`
Branches: `cleanup/security`, `cleanup/structure`, `cleanup/pipelines/*`,
`cleanup/python/*`, `cleanup/ci`, `cleanup/docs`,
`cleanup/pipelines/lifecycle`

Impact ranking inside each section: high → medium → low.

---

## 1. Security  → `cleanup/security`

_Leaked secrets, credential hygiene, `.gitignore` gaps. Connection IDs are
out of scope (see top of file)._

### High
### Medium

### Low

---

## 2. Structure  → `cleanup/structure`

_Directory layout, naming conventions, redundant nesting, stale paths._

### High

### Medium

### Low

---

## 3. Pipelines  → `cleanup/pipelines/*`

_Orchestra YAML: schema validity, missing alerts/retries/tags, missing header
comments. Connection IDs are out of scope. Split by subtree below._

_Policy note: for `orchestra/*.yml|yaml`, missing top-of-file showcase header comments and missing `configuration.retries` are intentionally ignored._

### `cleanup/pipelines/orchestra-core` — `orchestra/**/*.yml`
### `cleanup/pipelines/dbt-blueprints` — `dbt_projects/**/*.yml`

### `cleanup/pipelines/metadata-api` — `metadata_api/**/*.yml`

### `cleanup/pipelines/patterns` — `patterns/**/*.yml`

---

## 4. Python  → `cleanup/python/*`

_Ruff/format, type hints, dedup, parameter handling. Split by subtree below._

### `cleanup/python/workers` — `python/**/*.py`

### `cleanup/python/metadata-api` — `metadata_api/**/*.py`

### `cleanup/python/bauplan-estuary-dlt` — `bauplan/**`, `estuary/**`, `dlt/**`

### `cleanup/python/azure-hybrid` — `azure/ml/**`, `hybrid_deploy/**`, `multi_workspace_test/**`

---

## 5. CI  → `cleanup/ci`

_GitHub Actions, Makefile, pre-commit. Reserved files: anyone wanting a CI
change adds a request under "Cross-cutting follow-ups" below._

### High

### Medium

---

## 6. Docs  → `cleanup/docs`

_Root README, per-dir READMEs, generated PIPELINES.md. Reserved files:
README.md and PIPELINES.md — only this agent edits them. Merges last._

### High

### Medium

---

## 7. Deps  → folded into `cleanup/python/*`

_Unpinned, unused, vulnerable. Each Python sub-agent handles deps for its
own subtree._


---

## Cross-cutting follow-ups

_Findings that don't fit a single branch, or that one agent surfaces while
working in someone else's territory. Owner agent picks these up after their
main PRs land._

---

## 8. Pipeline lifecycle cleanup  → `cleanup/pipelines/lifecycle`

_Optional scope expansion. Use Orchestra runtime metadata (via MCP/API) to
decide which pipelines should be fixed, deleted, or retained. This stream is
allowed when explicitly requested and remains separate from hygiene-only edits._

### CI-unreferenced pipeline YAMLs (reference scan)
The following Orchestra pipeline YAML files exist in this repo but are not referenced by any GitHub Actions workflow `paths:` filters (reference scan found only `orchestra/dq_metaengine.yml`, `orchestra/aws_glue_fivetran_dbt_lakehouse_demo.yml`, and `orchestra/gcp_iceberg_bauplan_lakehouse.yml`).
Consider these candidates for `keep` / `fix` / `delete` classification in the lifecycle cleanup stream.
- orchestra/agents/claude_dbt.yml
- orchestra/agents/claude_lightdash.yml
- orchestra/agents/templates/dbt_impact.yml
- orchestra/agents/templates/dbt_reviewer.yml
- orchestra/agents/templates/enrich_snowflake.yml
- orchestra/agents/templates/impact_analysis.yml
- orchestra/agents/templates/personalised_slack.yml
- orchestra/agents/templates/summarise_orchestra.yml
- orchestra/alteryx_dbt_snowflake_teams.yml
- orchestra/agentic_analytics_dbt_pipeline.yml
- orchestra/aws_snowflake_looker_dbt.yml
- orchestra/claude_mcp_agent_approvals.yml
- orchestra/databricks_fivetran_dbt_metadata.yml
- orchestra/dbt/ecs.yml
- orchestra/dbt/databricks/sao.yml
- orchestra/dbt/motherduck/poetry.yml
- orchestra/dbt/snowflake/basic.yml
- orchestra/dbt/snowflake/snowflake_dbt_state_aware.yaml
- orchestra/dlt_ecs_power_bi.yml
- orchestra/dq_snowflake.yml
- orchestra/dq_snowflake_recon_approval.yml
- orchestra/elt_aws.yml
- orchestra/estuary/test.yaml
- orchestra/fivetran_coalesce_powerbi.yml
- orchestra/fivetran_dbt_hightouch_snowflake.yml
- orchestra/fivetran_dbt_power_bi.yml
- orchestra/fivetran_dbt_sigma.yml
- orchestra/gcp_bigquery_python_tableau_fivetran.yml
- orchestra/metadata_api/orchestra_pipeline.yaml
- orchestra/metaengine_outputs.yml
- orchestra/motherduck_dbt_lightdash_dlt.yml
- orchestra/multi_workspace_test/a.yaml
- orchestra/parallel_elt.yml
- orchestra/pipeline_examples/agents_produce_agents.yaml
- orchestra/python_anomalies_slack.yml
- orchestra/python_bigquery_metadata.yml
- orchestra/python_dbt_claude.yml
- orchestra/python_fivetran_dbt_powerbi.yml
- orchestra/rivery_snowflake_dbt_accounting.yml
- orchestra/snowflake_dbt_python_meta.yml
### Decision criteria

Apply these checks before deleting any pipeline:

- [ ] pipelines <pipeline-id> — Confirm pipeline is inactive/deprecated OR has no successful runs within agreed retention window (default: 90 days) — Retrieve status and run history from Orchestra MCP/API
- [ ] pipelines <pipeline-id> — Confirm no downstream pipeline/task dependencies remain — Verify dependency graph from Orchestra MCP/API before delete
- [ ] pipelines <pipeline-id> — Confirm pipeline is not referenced by active CI workflows, docs, or example guides — Search `.github/workflows/**`, README files, and docs before delete
- [ ] pipelines <pipeline-id> — Capture owner sign-off (or explicit approval source) for delete/fix decision — Record decision rationale in PR description

### Execution workflow

- [ ] pipelines CLEANUP_PLAN.md:1 — Build inventory of candidate pipelines using Orchestra MCP/API (state, last run, dependency edges, owner) — Classify each as `keep`, `fix`, or `delete` with rationale
- [ ] pipelines orchestra/<pipeline>.yml:1 — For `fix` candidates, apply only scoped corrective edits and keep schema valid — Run `orchestra validate <file>` after each change
- [ ] pipelines orchestra/<pipeline>.yml:1 — For `delete` candidates, remove pipeline YAML and all direct references — Update workflows/docs/examples that mention removed pipelines
- [ ] pipelines <code-path>:1 — Remove subsequent now-unused code/scripts/tests introduced only for deleted pipelines — Confirm with lint/dead-code checks before merge
- [ ] pipelines repo:1 — Validate safety gates before merge (`make validate`, relevant lint/tests) — Block merge if dependency or reference checks fail

---

## Proposed branch plan

_Auditor lists the leaf branches it recommends spawning, with rough item
counts so you can decide whether to split further or merge sub-branches._

| Branch | Items | Est. PRs | Notes |
|---|---|---|---|
| cleanup/security | 17 | 1 | Keep security as one branch (per instruction); includes gitleaks + semgrep + env-file hygiene. |
| cleanup/structure | 11 | 1 | README/index alignment + naming normalization. |
| cleanup/pipelines/orchestra-core-a-m | 18 | 1 | Split orchestra-core by filename bands for reviewability. |
| cleanup/pipelines/orchestra-core-n-z | 18 | 1 | Second orchestra-core leaf split. |
| cleanup/pipelines/orchestra-core-special | 16 | 1 | Special/date-named pipelines and metadata gaps. |
| cleanup/pipelines/metadata-api | 1 | 1 | metadata_api pipeline metadata gaps. |
| cleanup/python/workers-core | 12 | 1 | ruff/type-hint/os.getenv cleanup in core workers. |
| cleanup/python/workers-integration-a | 10 | 1 | integration_a/postgres/reverse_etl focused cleanup. |
| cleanup/python/bauplan-estuary-dlt | 9 | 1 | dlt/bauplan lint, dead-code, large modules. |
| cleanup/python/azure-hybrid | 4 | 1 | azure/ml typing/lint plus scope sanity. |
| cleanup/ci | 8 | 1 | Add make validate, ruff, gitleaks, pip-audit checks. |
| cleanup/docs | 15 | 1 | Docs stays one final merge branch (per instruction). |
| cleanup/pipelines/lifecycle | TBD after MCP inventory | 1-2 | Uses Orchestra runtime metadata to decide keep/fix/delete and remove subsequent unused code. |

