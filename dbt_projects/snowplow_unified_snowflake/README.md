# snowplow_unified_snowflake

Runs the [Snowplow Unified data model](https://docs.snowplow.io/docs/modeling-your-data/modeling-your-data-with-dbt/dbt-models/dbt-unified-data-model/)
(`snowplow/snowplow_unified` 1.0.1) on **dbt v2** (`dbt-oss`, installed by
Orchestra with `package_manager: UV`) against Snowflake.

Source: `SNOWPLOW_TRACKING.ATOMIC.EVENTS`, via `snowplow__database` /
`snowplow__atomic_schema`. Same table as [`snowplow_snowflake_sao`](../snowplow_snowflake_sao).

Orchestra pipeline: "Snowplow Unified on dbt v2" in the Orchestra Demo Account,
inputs `dbt_branch` / `dbt_command`.

## Error log

| # | Error | Fix |
| --- | --- | --- |
| 1 | `dbt deps`: `PackageVersionMismatch` for snowplow_unified and snowplow_utils (`require-dbt-version <2.0.0`) | None needed. dbt-oss 2.0.8 only warns, so no vendoring. |
| 2 | `snowplow_unified_base_sessions_lifecycle_manifest`: `invalid identifier 'DVCE_SENT_TSTAMP'`. snowplow_utils' late-event filter is unconditional; `days_late_allowed: -1` doesn't remove it (unlike normalize). | `ATOMIC.EVENTS` turned out to have only 22 columns (checked via `INFORMATION_SCHEMA`), with no dvce_*, page_url* parts, refr_*, mkt_*, br_*, useragent, or web_page context. An `on-run-start` hook ([macros/create_snowplow_events_compat.sql](macros/create_snowplow_events_compat.sql)) builds `<target db>.SNOWPLOW_ATOMIC_COMPAT.EVENTS` over the raw table, adding the missing columns as typed NULLs. It also derives `page_urlhost`/`page_urlpath` from `page_url` and synthesizes a web_page context (`id = event_id`) on page_view events. `snowplow__atomic_schema` points the package at the view, and `snowplow__allow_null_dvce_tstamps: true` makes the late filter coalesce to `collector_tstamp`. `days_late_allowed` is back to its default of 3: with the coalesce, `-1` would filter out every row. |
| 3 | Build green (128/128), but `views`, `sessions` and `users` were empty while `base_events_this_run` had 1891 rows. | `filter_bots` on Snowflake is `not rlike(useragent, ...)`. With `useragent` NULL the predicate is NULL, so every row was dropped. Set `snowplow__ua_bot_filter: false`, since there's no user agent to filter on. A detour first: the package logs "`<scratch table>` does not exist" on every command, even when the table exists. That's a dbt v2 parse-time warning, not the cause. `adapter.get_relation` resolves these relations fine at execution, and `static_analysis: off` changed nothing, so it was reverted. |
| 4 | `not_null_snowplow_unified_views_this_run_dvce_created_tstamp` failed (1063 rows). | The compat view sets `dvce_created_tstamp = derived_tstamp` (inferred: there's no device clock in the source) instead of NULL. Unified also uses it to bucket page pings for engaged time. |

Recover from an empty or bad first load with `dbt build --full-refresh` (pipeline input
`dbt_command`). snowplow_utils only allows the full refresh because the connection's
target is named `dev` (`snowplow__dev_target_name`).

## Window-var tuning simulation (TEST ONLY, branch `claude/snowplow-unified-tuning-sim`)

Tests the `tune-snowplow-windows` skill on synthetic data at three volumes. Data comes from
[macros/sim/generate_snowplow_sim.sql](macros/sim/generate_snowplow_sim.sql): 34 days with a
planted late tail (0.1% of sessions held on device 2–6 days, 0.1% of events loaded 8–14 h
late), 0.5% bots, 0.2% multi-day human sessions. Each case ran an initial load to 2026-10-01
plus three daily increments. Baseline is package defaults; tuned is the skill's proposal.
Results from [macros/sim/sim_report.sql](macros/sim/sim_report.sql), run 2026-10-30.

| Scale (events/day) | Applied | Increment exec s (base → tuned) | Increment GB scanned (base → tuned) | Output vs baseline |
| --- | --- | --- | --- | --- |
| S (50k) | lookback 6→8, days_late 3→4, session_lookback 730→12, upsert 30→8 | 56 → 68 | 1.35 → 1.32 | +113 views, +22 sessions (late events recovered) |
| M (1M) | days_late 3→2, session_lookback 730→12, upsert 30→6 (lookback 6→7 skipped by the 20% rule) | 168 → 122 | 23.2 → 22.0 | −2,045 views, −369 sessions (narrowed days_late dropped events) |
| L (5M) | session_lookback 730→12, upsert 30→6 (days_late narrowing rejected after M) | 414 → 270 | 67.7 → 60.6 | identical (same sessions hash) |

Execution times are from Snowflake query history and are noisy: cases shared one
warehouse and overlapped. Bytes scanned are the steadier measure.

Findings, applied to the skill:
- `days_late_allowed` filters on device lateness (`dvce_sent - dvce_created`), not load lag.
- Its p99.9 isn't stable when the late tail is near 0.1% of events (74 h at S, 26–30 h at
  M/L, same distribution), which led M to propose narrowing to 2 days and lose data. The
  skill now picks the setting from a dropped-events-per-N-days curve.
- Session length read from the lifecycle manifest is capped at `max_session_days`, so it
  could never suggest raising it. It's now measured from the raw events.
- The 20% churn rule blocked a widening (lookback 6→7) the data needed. Widening when the
  metric is already past the setting now bypasses it.
- `session_lookback_days` / `upsert_lookback_days` cut about 5–10% of increment bytes and
  didn't change outputs: worth doing, but not the large win the skill promised.
- dbt v2 (dbt-oss 2.0.8) doesn't apply `+query_tag`; the report splits cost per step by
  Snowflake session timing instead.

### v2: one change at a time, scored against the raw events (2026-10-30)

v1 compared bundled changes against package defaults over 34 days of history, so it
couldn't say which change did what, or whether "default" was itself right. v2:

- **Data:** 1M events/day for 45 days ([generate_snowplow_sim.sql](macros/sim/generate_snowplow_sim.sql),
  `logged_in_pct: 30` so stitching has user_ids to map), with the same planted late tails.
- **Starting state:** one default build to 2026-10-01, then about a year of history added
  ([sim_v2.sql](macros/sim/sim_v2.sql) `sim_inflate_history`: 12 back-dated copies of the
  manifest, sessions and views, users back-dated). Every variant starts from a zero-copy
  clone of it, so they differ only in the setting under test.
- **Runs:** five daily increments per variant, `dbt run` only.
- **Truth:** the raw events. Every human page view loaded during the five days should be
  a row in `views`. Misses are bucketed by cause (`sim_eval`). Session totals are checked
  against raw event counts too.
- **Cost:** per model from `information_schema.query_history`, read in 2-minute slices
  (`sim_cost_sliced`). Rows written is the reliable volume measure. Bytes scanned for
  scratch tables swings 3x between query plans for the same rows. Execution time has
  about ±20% noise: two identical default runs measured 253 s and 317 s per run.

Accuracy: 1,400,400 page views expected. Default misses 1,796 (0.13%): 1,162 held on
device more than 3 days, 292 loaded more than 6 h late, 342 in quarantined multi-day
human sessions.

| Setting (default) | Value | Page views missed | Cost effect per daily run |
| --- | --- | --- | --- |
| `lookback_window_hours` (6) | 2 | 2,812 (+1,016 loaded 1–6 h late) | 12% fewer event rows |
| | 15 | 1,504 (load-lag misses → 0; under-counted sessions 1,289 → 286) | 28% more event rows |
| `days_late_allowed` (3) | 1 | 2,105 | none measurable |
| | 7 | 634 (device-lateness misses → 0) | none measurable |
| `max_session_days` (3) | 1 | 3,111 (quarantine 342 → 1,301) | 10% fewer event rows |
| | 7 | 1,464 (quarantine → 10) | 10% more event rows |
| `session_lookback_days` (730) | 30 / 7 | identical to default | manifest bytes −30% / −42% |
| `upsert_lookback_days` (30) | 10 / 3 | identical to default | views merge bytes −57% / −75% |
| `session_timestamp` (collector) | load_tstamp | 1,503 (load-lag misses → 0 even with a 1 h lookback) | 4% more event rows (6 h), 11% fewer (1 h); needs a fresh build |
| `session_stitching` (true) | false | identical to default (stitched ids not populated) | sessions model 123 s → 26 s, rows rewritten 21.5M → 0.65M per run; package time −30% |

Combined (`lookback 15, days_late 7, max_session 5, session_lookback 14, upsert 8`,
stitching on) against a default run at the same load: **2 page views missed instead of
1,796**, sessions missing 238 → 35, under-counted 1,289 → 8. Cost: 37% more event rows,
bytes 8.5 → 5.3 GB, time 135 → 143 s (within noise).

Findings:
- The window vars are mostly correctness settings. Only `session_lookback_days` and
  `upsert_lookback_days` are free cost savings. Both left outputs byte-identical here.
- The largest package cost is session stitching. Its post-hook UPDATE matches every
  historical row of every mapped user and rewrites about the whole sessions table each
  run (21M rows per run here, clustering depth 2 → 35 after five runs).
  [stitch_user_identifiers.sql](macros/stitch_user_identifiers.sql) tested skipping rows
  already holding the mapped id (via dispatch, var-gated). Outputs were identical, but
  Snowflake still rewrote the same volume in the same time, so it saves nothing.
  Disabling stitching is the only change that removed the cost.
- `users_sessions_this_run` reads every historical session of each returning user
  (7M rows per run). No var bounds it, so it grows with history.
- `ACCOUNT_USAGE` isn't readable by this role, so partition pruning wasn't measured.
