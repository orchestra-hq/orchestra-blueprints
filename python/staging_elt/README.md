# Staging ELT worker

`extract_load.py` is the **EL** step of
[`orchestra/staging_end_to_end_elt.yml`](../../orchestra/staging_end_to_end_elt.yml).

It simulates a source-system extract: it generates a deterministic batch of
records for one logical source, writes them to a newline-delimited JSON landing
file, and publishes the batch summary back to Orchestra via `orchestra-sdk` so
downstream **T** and **Downstream** tasks can reference it.

## Why it is standard-library only

The Orchestra Python task runtime pre-installs `orchestra-sdk`, and everything
else this worker needs is in the standard library. That keeps the build step
trivial and the staging run fast, which is the point of a smoke-test blueprint.

## Environment variables

| Variable | Purpose | Default |
| --- | --- | --- |
| `SOURCE_NAME` | Logical source being extracted | `unknown_source` |
| `TARGET_TABLE` | Destination table for the batch | value of `SOURCE_NAME` |
| `ENV_NAME` | Deployment environment | `staging` |
| `BATCH_SIZE` | Rows to simulate | `250` |
| `LANDING_DIR` | Landing-file directory | `./landing` |

`ORCHESTRA_API_KEY`, `ORCHESTRA_PIPELINE_RUN_ID` and `ORCHESTRA_TASK_RUN_ID` are
injected by Orchestra at runtime. Without an API key the script still runs and
simply skips publishing outputs, so it is safe to run locally:

```bash
SOURCE_NAME=hubspot_contacts TARGET_TABLE=hubspot_contacts_raw BATCH_SIZE=10 \
  python extract_load.py
```

## Outputs

With `set_outputs: true` on the task, the worker sets `rows_loaded`, `batch_id`,
`target_table` and `load_summary`. The pipeline wires these into the Slack run
summary via
`${{ ORCHESTRA.PIPELINE_RUN_TASKS['python_extract_load'].OUTPUTS['batch_id'] }}`.
