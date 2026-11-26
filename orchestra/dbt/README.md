# dbt Core pipelines

## `snowflake/node_anomaly_detection.yml`

The node-level anomaly detection demo: one `dbt build` Task over
[`dbt_projects/snowflake_anomaly`](../../dbt_projects/snowflake_anomaly),
carrying both `operation_duration_above_baseline` and
`operation_duration_below_baseline`, each notifying Slack `alert-demos`.

An *operation* is one dbt node. The Task declares the monitor and the thresholds;
each model opts itself in from its `meta` (`orchestra_anomaly_detection`, plus
optional `orchestra_anomaly_percentage_above_baseline`,
`..._percentage_below_baseline`, `..._min_baseline_seconds` and `channel`
overrides). Both halves are required — a Task with no `anomalies` block monitors
nothing however its models are configured, and vice versa.

| Setting | Task | `fct_orders` | `dim_customers` |
|---|---|---|---|
| above baseline | 30% | **50%** | 30% |
| below baseline | 60% | **60%** | 60% |
| `min_baseline_seconds` | 0 | 0 | 0 |
| Slack | `alert-demos` | **`#alert-demos`** via `channel` | `alert-demos` |

`min_baseline_seconds: 0` is what keeps a two-second model in scope; a real mart
would set it well above the noise floor instead. `operation_types:
[MATERIALISATION]` limits the monitor to models — leaving it out would cover
every type except `TEST`/`TEST_GROUP`, and naming `TEST` is how tests get
monitored.

### Making it fire

A baseline is the **median of the previous qualifying runs**: succeeded or
warned, same environment, on the default branch or a published version, within
30 days, most recent 100 — and **at least ten of them**. Below ten there is no
baseline and nothing fires, so the demo is a warm-up then a spike:

1. Merge to `main`. Runs on a feature branch never count toward a baseline, so
   nothing before the merge builds one.
2. Run it ten or more times on defaults (`fct_orders_seconds: 2`). Each run takes
   a few seconds. These are the baseline.
3. Run it once with `fct_orders_seconds: 90`. That is 45x the ~2s median, far past
   the 50% `fct_orders` asks for, so the run is flagged and Slack gets the alert.
   `dim_customers`, untouched at 0s, is not.
4. Run it again on defaults. `fct_orders` is now fast relative to a median the
   slow run has dragged upward — set `dim_customers_seconds: 30` for a few runs
   and then drop it back to `0` to trip the below-baseline monitor cleanly.

`max_anomalies: 5` caps how many nodes are *notified* per collection, furthest
from baseline first; the rest are still recorded and returned by the API.
