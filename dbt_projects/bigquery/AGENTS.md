# AGENTS.md — rules for agents working on this dbt project

Team-owned. Agents read this; they do not edit it.

This project is small on purpose: `raw.raw_orders` → `stg_orders` (view,
relation `Stg Orders Clean`) → `orders_daily` (table), all in the BigQuery
dataset `dbt_sao_demo`. See [README.md](README.md) for how the sources are
recreated if the dataset is wiped.

## Where the context lives

| File | Owner | What it holds |
| --- | --- | --- |
| `AGENTS.md`, `models/*/AGENTS.md` | Team | Rules: how this project is modelled, tested and debugged |
| `.agent/conventions.md` | Team | Naming, materialisation and testing conventions |
| `KNOWN_TEST_WARNINGS.yml` | Team + agent | Triaged tests, with a baseline and the threshold that re-flags them |
| `.agent/knowledge.yml` | Agent, via PR | What fixed each node before, and what did not |
| `.claude/skills/dbt-debug/SKILL.md` | Team | The debug procedure: what to read before a fix, what to write after |

None of these are on a dbt path, so nothing here changes what dbt builds.

## When a run fails

Follow `.claude/skills/dbt-debug/SKILL.md`. In short: read known warnings,
the run's artifacts, the failing nodes' ancestors, then matching notes and
conventions — before proposing a fix.

## Guardrails

- Write only to `.agent/**`, `KNOWN_TEST_WARNINGS.yml` and the failing model's
  own SQL/YAML. Never edit this file, `README.md` or `dbt_project.yml`.
- Branch and push only. Never commit to `main`.
- No `--full-refresh` against production without a human's approval.
- Stop after 3 failed fix attempts on the same node and escalate.
- Never delete a note in `.agent/knowledge.yml`; mark it `confidence: stale` instead.
