# dummy_motherduck

The dbt half of the **dummy end-to-end blueprint** —
[`orchestra/dummy_end_to_end.yml`](../../orchestra/dummy_end_to_end.yml). Four
models over MotherDuck, whose job is to be built by the pipeline and to trip
Orchestra's **node-level anomaly detection**.

- **Profile:** `motherduck` — the profile name on the Orchestra dbt Core
  connection `dbt_motherduck__prod__39243`, not this project's name.
  `profiles.yml` is gitignored repo-wide; in Orchestra it comes from the
  connection.
- **Output schema:** `<connection schema>_dummy_demo`, so it never lands beside
  anything the other `dbt_projects/motherduck_*` projects own.
- **No sources, no seeds.** Both staging models generate their rows inline from
  `range()`, so there is nothing to seed, nothing to keep fresh, and nothing to
  drop. The row count comes from the upstream Python Task via the
  `dummy_row_count` var.

## The DAG

| Model | Materialisation | Monitored? | Where that comes from |
|---|---|---|---|
| `stg_dummy_orders` | view | no | `config.meta.orchestra_anomaly_detection: false` in `models/staging/schema.yml` |
| `stg_dummy_customers` | view | no | same |
| `dim_dummy_customers` | table | yes, at 30% | inherits the project-wide `+meta` opt-in and the `marts` folder's `+meta` percentage |
| `fct_dummy_orders` | table | yes, at 50% | its own `config.meta` in `models/marts/schema.yml`, which also sets `channel` |

That spread is deliberate — it exercises every layer of precedence. dbt merges
`meta` most-specific-wins, so the project-wide opt-in in `dbt_project.yml`
reaches all four models, the `marts` folder narrows the percentage for
`dim_dummy_customers`, `fct_dummy_orders` overrides it again, and the two
staging models opt themselves back out.

Verify what dbt actually resolved without touching MotherDuck:

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

The tests are **not** monitored, because an anomaly with `operation_types:
[MATERIALISATION]` covers models only. Name `TEST` in the Task's
`operation_types` to bring them in.

## The slow knob

`fct_dummy_orders` and `dim_dummy_customers` each carry a `pre_hook` built by
the `spin_hook` macro. dbt counts hook time inside the node's own execution
timing, which is the number Orchestra compares against the baseline.

DuckDB has no sleep function, so unlike the `system$wait` hook in
[`dbt_projects/snowflake_anomaly`](../snowflake_anomaly) this is **approximate
load rather than an exact delay**: the macro turns the seconds you ask for into
a row count to hash, at a calibration constant of 30M rows/second measured on a
single core. MotherDuck runs multi-threaded, so expect the real elapsed time to
come in *under* what you asked for — dial up until the model is visibly slow
rather than treating the number as a stopwatch.

```bash
dbt build --profiles-dir . --vars '{"fct_dummy_orders_seconds": 90}'
```

At `0` the macro returns no hook at all, so the model is simply fast.

| var | default | what it is for |
|---|---|---|
| `dummy_row_count` | `500` | rows the staging models generate; set from the Python Task's `row_count` output |
| `fct_dummy_orders_seconds` | `2` | the model the demo makes slow |
| `dim_dummy_customers_seconds` | `0` | a second lever, for showing two nodes flagged at once |

## Running it in Orchestra

[`orchestra/dummy_end_to_end.yml`](../../orchestra/dummy_end_to_end.yml) is the
pipeline;
[`python/dummy_pipeline/README.md`](../../python/dummy_pipeline/README.md) has
the run sequence — a baseline needs at least ten qualifying runs before
anything can fire.
