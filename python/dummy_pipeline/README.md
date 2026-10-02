# dummy_pipeline

The Python half of the **dummy end-to-end blueprint** —
[`orchestra/dummy_end_to_end.yml`](../../orchestra/dummy_end_to_end.yml). It is
deliberately the smallest thing that still has a real shape: extract, hand a
value downstream, get monitored.

`extract_dummy_orders.py` generates a deterministic batch of fake orders, writes
them to CSV, and publishes the batch size as the Orchestra Task output
`row_count`. The dbt Task downstream reads that output as the `dummy_row_count`
dbt var, so the two halves are wired together rather than merely ordered —
Orchestra Task outputs are only readable by another Task in the same pipeline.

| Env var | Default | What it does |
|---|---|---|
| `DUMMY_ROW_COUNT` | `500` | How many dummy orders to generate. Set from the pipeline's `row_count` input. |
| `DUMMY_SEED` | `42` | Fixed so repeated runs are identical, which is what makes a stable duration baseline possible. |
| `DUMMY_OUTPUT_PATH` | `dummy_orders.csv` | Where the batch lands. |

Run it locally with `ORCHESTRA_API_KEY` set, or drop the `set_output` call to
run it with no Orchestra at all.

## The blueprint

Three monitoring layers, on one pipeline:

| Layer | Where it is declared | What it watches |
|---|---|---|
| Pipeline | `anomalies` at the root of the YAML | `pipeline_duration_above_baseline` / `..._below_baseline`, 30% / 60% |
| Task | `anomalies` on the Python Task | `task_duration_above_baseline`, 30% |
| Operation (dbt node) | `anomalies` on the dbt Task **and** `meta` on each model | `operation_duration_above_baseline` / `..._below_baseline`, `MATERIALISATION` only |

Both halves of the node-level pair are required — a Task with no `anomalies`
block monitors nothing however its models are configured, and a model that never
opts in from its `meta` is not monitored however the Task is configured. See
[`dbt_projects/dummy_motherduck/README.md`](../../dbt_projects/dummy_motherduck/README.md)
for which model opts in where.

Alerts are separate from anomalies and fire on status, not duration: `FAILED` on
the Python Task, `FAILED`/`WARNING` on the dbt Task, and a pipeline-level
`FAILED`/`WARNING` catch-all. All of them notify Slack `alert-demos`.

## Making the anomalies fire

A baseline is the **median of the previous qualifying runs**: succeeded or
warned, same environment, on the default branch or a published version, within
30 days, most recent 100 — and **at least ten of them**. Below ten there is no
baseline and nothing fires, so the demo is a warm-up then a spike:

1. Merge to `main`. Runs on a feature branch never count toward a baseline.
2. Run it ten or more times on defaults. These are the baseline.
3. Run it once with `fct_dummy_orders_seconds: 90`. That is far past the 50%
   `fct_dummy_orders` asks for, so the node is flagged and Slack gets the alert
   — and because the whole run is dragged out with it, the pipeline-level
   monitor is likely to fire too. `dim_dummy_customers`, untouched at 0s, is
   not.
4. Run it again on defaults. `fct_dummy_orders` is now fast relative to a median
   the slow run dragged upward — set `dim_dummy_customers_seconds: 30` for a
   few runs and then drop it back to `0` to trip the below-baseline monitor
   cleanly.

Every threshold here is loose and every `min_baseline_seconds` is `0`, which is
what keeps a few-second demo in scope. A real pipeline would set the floor well
above its noise band instead.
