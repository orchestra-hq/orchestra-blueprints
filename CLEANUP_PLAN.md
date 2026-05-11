# Cleanup Plan

> Filled in by the Auditor agent. Specialist agents read their assigned section
> and only act on items tagged for their branch. Check items off as PRs land.

**Status:** 🟡 awaiting auditor run
**Auditor commit:** _pending_
**Last updated:** _pending_

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
"Cross-cutting follow-ups" for later work.

---

## How to read this file

Each finding is one checkbox line:

`- [ ] <tag> <file:line> — <finding> — <suggested fix> — <branch>`

Tags: `structure | pipelines | python | dbt | security | docs | ci | deps`
Branches: `cleanup/security`, `cleanup/structure`, `cleanup/pipelines/*`,
`cleanup/python/*`, `cleanup/ci`, `cleanup/docs`

Impact ranking inside each section: high → medium → low.

---

## 1. Security  → `cleanup/security`

_Leaked secrets, credential hygiene, `.gitignore` gaps. Connection IDs are
out of scope (see top of file)._

### High
- [ ] _auditor fills in_

### Medium
- [ ] _auditor fills in_

### Low
- [ ] _auditor fills in_

---

## 2. Structure  → `cleanup/structure`

_Directory layout, naming conventions, redundant nesting, stale paths._

### High
- [ ] _auditor fills in_

### Medium
- [ ] _auditor fills in_

### Low
- [ ] _auditor fills in_

---

## 3. Pipelines  → `cleanup/pipelines/*`

_Orchestra YAML: schema validity, missing alerts/retries/tags, missing header
comments. Connection IDs are out of scope. Split by subtree below._

### `cleanup/pipelines/orchestra-core` — `orchestra/**/*.yml`
- [ ] _auditor fills in_

### `cleanup/pipelines/dbt-blueprints` — `dbt_projects/**/*.yml`
- [ ] _auditor fills in_

### `cleanup/pipelines/metadata-api` — `metadata_api/**/*.yml`
- [ ] _auditor fills in_

### `cleanup/pipelines/patterns` — `patterns/**/*.yml`
- [ ] _auditor fills in_

---

## 4. Python  → `cleanup/python/*`

_Ruff/format, type hints, dedup, parameter handling. Split by subtree below._

### `cleanup/python/workers` — `python/**/*.py`
- [ ] _auditor fills in_

### `cleanup/python/metadata-api` — `metadata_api/**/*.py`
- [ ] _auditor fills in_

### `cleanup/python/bauplan-estuary-dlt` — `bauplan/**`, `estuary/**`, `dlt/**`
- [ ] _auditor fills in_

### `cleanup/python/azure-hybrid` — `azure/ml/**`, `hybrid_deploy/**`, `multi_workspace_test/**`
- [ ] _auditor fills in_

---

## 5. CI  → `cleanup/ci`

_GitHub Actions, Makefile, pre-commit. Reserved files: anyone wanting a CI
change adds a request under "Cross-cutting follow-ups" below._

### High
- [ ] _auditor fills in_

### Medium
- [ ] _auditor fills in_

---

## 6. Docs  → `cleanup/docs`

_Root README, per-dir READMEs, generated PIPELINES.md. Reserved files:
README.md and PIPELINES.md — only this agent edits them. Merges last._

### High
- [ ] _auditor fills in_

### Medium
- [ ] _auditor fills in_

---

## 7. Deps  → folded into `cleanup/python/*`

_Unpinned, unused, vulnerable. Each Python sub-agent handles deps for its
own subtree._

- [ ] _auditor fills in_

---

## Cross-cutting follow-ups

_Findings that don't fit a single branch, or that one agent surfaces while
working in someone else's territory. Owner agent picks these up after their
main PRs land._

- [ ] _added during execution_

---

## Proposed branch plan

_Auditor lists the leaf branches it recommends spawning, with rough item
counts so you can decide whether to split further or merge sub-branches._

| Branch | Items | Est. PRs | Notes |
|---|---|---|---|
| _auditor fills in_ | | | |

---

## Done

_Move completed items here with the merging PR number, so the live sections
stay focused on remaining work._

- [x] _example: pipelines — orchestra/snowflake_demo.yml missing alerts — #42_
