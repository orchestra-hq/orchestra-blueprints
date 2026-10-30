---
name: tune-snowplow-windows
description: Measure the Snowplow Unified project's event lateness, session shape and scan cost in Snowflake, then propose changes to its window vars (lookback, late events, session length, session lookback, upsert lookback, backfill) and to clustering on the events table. Use when asked to tune, right-size or cut the cost of the Snowplow Unified dbt run, or when its runs get slower or more expensive.
---

# Tune the Snowplow Unified window vars

Project: `dbt_projects/snowplow_unified_snowflake`. The vars live under `vars:` in
its `dbt_project.yml`. Anything not set there uses the package default.

## 1. Measure (SQL)

Run both queries on the Snowflake connection and keep the results.

- [window_metrics.sql](window_metrics.sql): one row per metric, with the var it informs.
  It covers the last 30 days of events, anchored on the newest event.
- [scan_metrics.sql](scan_metrics.sql): for each Unified model over the last 14 days,
  the rows written, execution time and bytes per run, plus the stitching UPDATEs.
  It needs `ACCOUNT_USAGE` access. If that's refused, run the same query against
  `<db>.information_schema.query_history()`, which keeps 7 days and returns at most
  10,000 rows per call, and say so. On a busy warehouse, query it in short time slices.
- `select system$clustering_information('<raw events table>', '(collector_tstamp)')`:
  `average_depth` and the overlap histogram.

If the table names in the SQL don't match the target (the database or schema moved,
or the package's `+schema` changed), fix them in the files before running.

## 2. Add run context

From the dbt artifacts and Orchestra logs for the recent runs:

- `run_results.json`: `execution_time` per model, and whether
  `snowplow_unified_base_events_this_run` dominates.
- The run log's `Snowplow:` lines: the processed window
  (`lower_limit` / `upper_limit`) and whether the run took the "out of sync" or
  "new model" path. Either one means a wider scan than the vars suggest.
- Whether runs are hitting their timeout or catching up on a backlog.

## 3. Work out values

Treat a metric as missing if its sample is too small to trust: fewer than about
10,000 events or 1,000 sessions in the window. Don't propose a change from it.

The vars fall into two groups, and they trade off differently. These figures come from a
simulation at 1M events a day with a year of history, where each var was changed on its
own and scored against the raw events (see the project README, "v2").

**Correctness vars.** These decide which events are kept. Setting them too low drops data
for good, and widening them costs little.

| Var (package default) | Rule | Measured effect |
| --- | --- | --- |
| `snowplow__lookback_window_hours` (6) | ≥ `late_hours_max`, rounded up to a whole hour. If that's over about 24 h, propose `session_timestamp: load_tstamp` instead. | Each uncovered hour of load lag loses those events. 2 h missed 1,016 more page views than 6 h. Going 6 → 15 h added about 28% event rows per run, roughly 3% per hour. |
| `snowplow__days_late_allowed` (3) | The smallest N whose `device_late_events_over_Nd` is negligible (under about 0.001% of `events_in_window`). It filters on how long the device held the event (`dvce_sent_tstamp - dvce_created_tstamp`), not load lag. Don't use a percentile: p99.9 read 74 h on one sample and 26 h on another from the same distribution. | Widening had no measurable cost (3 → 7 recovered 1,162 page views). Narrowing to 1 lost 309. |
| `snowplow__max_session_days` (3) | ≥ the p99.9 of human session length from the raw events, excluding bot user agents, rounded up. The lifecycle manifest caps sessions at the current setting, so don't read length from it. | Each day costs about 5% more event rows. 1 day quarantined 4x as many sessions (342 → 1,301). 7 days left 10. |
| `snowplow__session_timestamp` (`collector_tstamp`) | Propose `load_tstamp` when the load-lag tail is long. It needs a full refresh, so leave the decision to a human. | Late-loaded misses dropped to 0, even with a 1 h lookback, which processed 11% fewer event rows than the default. |

**Cost vars.** These left outputs byte-identical at every value tested, so they're the
free savings.

| Var (package default) | Rule | Measured effect |
| --- | --- | --- |
| `snowplow__session_lookback_days` (730) | ≥ `max_session_days` + 2, minimum 7 | 7 days cut manifest bytes by 42% |
| `snowplow__upsert_lookback_days` (30) | ≥ `ceil(lookback_window_hours / 24)` + 2, minimum 3 | 3 days cut views-merge bytes by 75% |
| `snowplow__backfill_limit_days` (30) | Days that fit within about half the run's time budget, from elapsed time per day processed | Changes how much each run processes, not the results |

**Package costs no var reaches.** Report these with their numbers, but don't put them in
the PR.

- **Session stitching** (`snowplow__session_stitching`, default true). Its post-hook
  UPDATE rewrites about the whole sessions table on every run: in testing, 21M rows per
  run, about half the package's run time, and clustering depth 2 → 35 in five runs.
  - Skipping rows that already hold the mapped id saves nothing; Snowflake rewrites the
    same volume.
  - Only `session_stitching: false` removes the cost.
  - Propose it only when nothing downstream reads `stitched_user_id`, and say so.
- **`users_sessions_this_run`** rereads every past session of each returning user, so its
  cost grows with history. Fixing it means overriding the package model.

How to compare cost:
- Use rows written and per-model execution time from query history.
- Don't trust bytes scanned for the `*_this_run` scratch tables. The same rows can scan
  3x more or less depending on the query plan.
- Execution time varies about ±20% between identical runs, so ignore smaller changes.

Clustering on `collector_tstamp`:
- Recommend it only when `scan_ratio` stays well above the share of the table a run
  should read, and `average_depth` is high.
- Snowplow loaders append in rough time order, so the table is often clustered well
  enough already. Automatic clustering costs credits, so weigh that against the scan
  savings.

## 4. Decide what to change

- **Cost vars** (`backfill_limit_days`, `session_lookback_days`,
  `upsert_lookback_days`): change them freely, as long as they stay at or above their
  floors. `backfill_limit_days` can also be passed at run time with
  `dbt build --vars '{snowplow__backfill_limit_days: N}'`.
- **Correctness vars**:
  - Widen them whenever a metric says data is being dropped. It costs a few percent
    more event rows.
  - Propose narrowing them only when the cost data justifies it. Show the events it
    would drop, and leave the decision to a human.
  - Changing `max_session_days`, `days_late_allowed` or `session_timestamp` doesn't fix
    data already processed. Say whether a `--full-refresh` (with a temporary large
    `backfill_limit_days`) is needed for the change to apply to history.
    `session_timestamp` always needs one.

Skip a change smaller than about 20%, so the vars don't churn from week to week.
This doesn't apply when the metric is already past the current value (for example
load lag p99.9 of 7 hours against a 6-hour lookback). That's data being lost now,
so widen it.

## 5. Propose

Open a PR against `main` that edits only the `vars:` in `dbt_project.yml`. Leave a
comment on each changed var naming the metric and date it came from. The PR
description must include:

- a table of each var's current value, proposed value, the metric behind it and the
  sample size;
- the clustering recommendation with its numbers, applied by hand rather than in
  the PR;
- every metric you skipped as untrustworthy, and why;
- whether a full refresh is needed.

If nothing passes the thresholds, open no PR. Report the metrics and say the current
values hold.
