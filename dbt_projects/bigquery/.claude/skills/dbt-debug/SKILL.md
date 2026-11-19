---
name: dbt-debug
description: Debug a failed dbt run in this project using the repo's own context — known warnings, run artifacts, ancestors, learned notes and conventions — then record what was learned on a daily knowledge branch. Use whenever a dbt build of dbt_projects/bigquery fails.
---

# dbt-debug

You are debugging a failed `dbt build` of `dbt_projects/bigquery`. All paths
below are relative to that directory. Read `AGENTS.md` first; its guardrails
override anything here.

## 1. Read — before proposing any fix

Work through these in order and stop as soon as one explains the failure.

1. **Known warnings** — `KNOWN_TEST_WARNINGS.yml`. If every failing node has an
   entry and is inside its `reflag_when` threshold, the failure is known: say
   so, change no code, and skip to step 3.
2. **Run artifacts** — from the Orchestra MCP, get the failed dbt task run
   (its ID is in your prompt) and download `run_results.json` and
   `manifest.json`. List every node with status `error` or `fail`, with its
   message and, for tests, the failure count.
3. **Ancestors** — for each failing node, walk `parent_map` in the manifest up
   to its sources. Query the warehouse for the ancestors as they are *now*
   (row counts, max dates, the rows a failing test returns), not as you
   assume them to be.
4. **Notes and conventions** — find every entry in `.agent/knowledge.yml`
   whose `unique_id` is a failing node or one of its ancestors, and read
   `.agent/conventions.md` plus the `AGENTS.md` in the failing model's folder.
   A `confirmed` note is strong evidence; a `candidate` note is a lead. Never
   retry anything listed under `tried_and_failed`.

Then decide: **code bug** (fix the model), **data/timing** (no code change —
explain, and propose a `KNOWN_TEST_WARNINGS.yml` entry if it will recur), or
**unknown** (escalate).

## 2. Fix — only for a code bug

- Branch `agent-fix/<pipeline_run_id>` from the branch named in your prompt. One branch per incident.
- Touch only the failing model's SQL/YAML.
- Verify with the dbt Core connection, selecting only the failing node and its
  children. Never `--full-refresh`.
- After 3 failed attempts on the same node, stop, record them under
  `tried_and_failed`, and escalate.

## 3. Write — after the rerun, every time

Record what you learned on the **daily knowledge branch**
`agent-kb/<YYYY-MM-DD>` (UTC). If it already exists, check it out and add to
it; otherwise create it from the branch named in your prompt (`main` unless
said otherwise). One branch per day batches all of the
day's lessons into one human review.

In `.agent/knowledge.yml`:

- **Existing note matches** (same `unique_id` and the same cause): increment
  `seen`, append the pipeline run ID to `runs`, and promote `candidate` to
  `confirmed` once `seen` reaches 3.
- **New lesson**: append a note with `confidence: candidate`, `seen: 1`.
- **A fix you tried that did not work**: add it to `tried_and_failed` on the
  relevant note — failed attempts are always recorded.
- **A note that matched but was wrong**: set `confidence: stale`. Never delete.

If the failure is a recurring data/timing issue, also add an entry to
`KNOWN_TEST_WARNINGS.yml` with `owner: agent`, a concrete `baseline` and a
`reflag_when` threshold.

Commit with a message like
`agent-kb: <unique_id> <added|bumped> (run <short run id>)` and push the
branch. Do not merge it.

## 4. Report

End with: the failing nodes, root cause, which context files you used (and
whether they helped), what you changed or "no code change", and the branch(es)
you pushed.
