# Incident grouping end-to-end test

The DAGs from the ENG-12727 grouping diagram, A → B → C and D → E, on a local DuckDB file, so
any staging workspace can run them without warehouse credentials.

Each run picks what breaks with the `fail` var, a comma-separated list of nodes:

| Node | What breaks |
| --- | --- |
| `a`, `b`, `c`, `d`, `e` | That model errors at runtime, so the models below it are skipped |
| `a_warn` | A warning test on model A |
| `orphan` | An erroring test that refs no model, so its failure has no asset |

```bash
dbt build --vars '{"fail": "b,d"}'
```

The connection's `profiles.yml` needs an `incident_grouping_e2e` profile with a `dev` DuckDB
target. Running with any other `--target` fails before dbt builds anything, which stands in for
an infrastructure failure. `orchestra/dbt/duckdb/incident_grouping_e2e.yml` is the pipeline.
