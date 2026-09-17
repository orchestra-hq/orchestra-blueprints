# snowflake_anomaly

A four-model dbt Core project whose only job is to trip Orchestra's
**node-level anomaly detection**: the `operation_duration_above_baseline` /
`operation_duration_below_baseline` monitors that a Task declares and individual
models opt into from their `meta`.

- **Profile:** `snowflake_airflow_dbt` — the profile name on the Orchestra dbt
  Core connection `dbt_snowflake_blueprints_prod_07025`, not this project's name.
  `profiles.yml` is gitignored repo-wide; in Orchestra it comes from the
  connection, and locally copy the one in `dbt_projects/snowflake`.
- **Output schema:** `<connection schema>_anomaly_demo`, so it never lands beside
  anything `dbt_projects/snowflake` owns.
- **No sources.** Both staging models generate their rows inline, so there is
  nothing to seed, nothing to keep fresh, and nothing to drop.

## The DAG

| Model | Materialisation | Monitored? | Where that comes from |
|---|---|---|---|
| `stg_orders` | view | no | `config.meta.orchestra_anomaly_detection: false` in `models/staging/schema.yml` |
| `stg_customers` | view | no | same |
| `dim_customers` | table | yes, at 30% | inherits the project-wide `+meta` opt-in and the `marts` folder's `+meta` percentage |
| `fct_orders` | table | yes, at 50% | its own `config.meta` in `models/marts/schema.yml`, which also sets `channel` |

That spread is deliberate — it exercises every layer of precedence the docs
describe. dbt merges `meta` most-specific-wins, so the project-wide opt-in in
`dbt_project.yml` reaches all four models, the `marts` folder narrows the
percentage for `dim_customers`, `fct_orders` overrides it again, and the two
staging models opt themselves back out.

Verify what dbt actually resolved without touching Snowflake:

```bash
dbt parse --profiles-dir .
python3 -c "
import json
m = json.load(open('target/manifest.json'))
for n in sorted(m['nodes'].values(), key=lambda n: n['name']):
    if n['resource_type'] == 'model':
        print(n['name'], n['config']['meta'])
"
```

The eight tests are **not** monitored, because an anomaly with no
`operation_types` covers every type except `TEST` and `TEST_GROUP`. Name `TEST`
in the Task's `operation_types` to bring them in.

## The slow knob

`fct_orders` and `dim_customers` each carry a `pre_hook` built by the
`pause_hook` macro, which emits `select system$wait(N, 'SECONDS')` — an exact
delay, rather than a query tuned to be slow. dbt counts hook time inside the
node's own execution timing, which is the number Orchestra compares against the
baseline.

```bash
dbt build --profiles-dir . --vars '{"fct_orders_seconds": 90}'
```

At `0` the macro returns no hook at all, so the model is simply fast.

| var | default | what it is for |
|---|---|---|
| `fct_orders_seconds` | `2` | the model the demo makes slow |
| `dim_customers_seconds` | `0` | a second lever, for showing two nodes flagged at once |

## Running it in Orchestra

[`orchestra/dbt/snowflake/node_anomaly_detection.yml`](../../orchestra/dbt/snowflake/node_anomaly_detection.yml)
is the pipeline, and its README section has the run sequence — a baseline needs
at least ten qualifying runs before anything can fire.
