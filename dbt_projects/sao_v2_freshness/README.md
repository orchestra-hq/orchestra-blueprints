# SAO on dbt v2: source freshness test

One small project per warehouse (BigQuery, Snowflake, Databricks), each with a
source of every kind `dbt-orchestra` has to judge freshness for on dbt v2, and
one table model on each:

| Source | Freshness from | Model |
| --- | --- | --- |
| `fresh_field.raw_field` | `loaded_at_field` | `stg_field` |
| `fresh_query.raw_query` | `loaded_at_query` | `stg_query` |
| `fresh_implicit.raw_implicit` | dbt v2 metadata freshness | `stg_implicit` |
| `fresh_view.raw_view` (a view) | none: always counts as changed | `stg_view` |

Everything lives in the `sao_v2_fresh` schema, so its SAO state is separate from
the other demo projects. `requirements.txt` pins `dbt-orchestra` to a sao-paolo
`main` commit, because the view-source handling is newer than the 1.4.0 release.

Run order:

1. `dbt run-operation sao_v2_setup` creates the sources (recreating them counts
   as new data).
2. `dbt build` with state orchestration: cold, then warm.
3. `dbt run-operation sao_v2_insert --args '{table: raw_field}'`, then build
   again: only `stg_field` (and `stg_view`) should rebuild.
