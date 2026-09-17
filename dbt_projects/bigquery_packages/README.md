# bigquery_packages

The `bigquery` blueprint plus a package dependency, pinned to dbt 2.x. It exists
so a dbt Core task can exercise `dbt deps` and a package macro against real
sources without touching any production dataset.

- **Profile:** `dbt_bigquery` — the profile name on the Orchestra dbt Core
  connection `dbt_core__bigquery__01406`, not this project's name.
- **Output dataset:** `dbt_sao_demo`, pinned by `generate_schema_name`. Models
  carry a `_pkg` suffix so they sit alongside the `bigquery` project's
  `stg_orders` / `orders_daily` in the same dataset rather than clobbering them.
- **Sources:** `raw.raw_orders` and `crm.raw_customers`, the standing tables the
  `bigquery` blueprint documents. This project reads them and owns neither, so
  there is nothing to load before a first run. See that project's README for the
  `CREATE OR REPLACE TABLE` statements if the dataset is ever wiped.
- **Lineage:** `raw.raw_orders` → `stg_orders_pkg` (view) → `orders_daily_pkg`
  (table).

## The package

`dbt-labs/dbt_utils` at **1.4.1** — any package would do; this one is small and
already used elsewhere in the repo. The version matters: 1.4.1 is the first
release whose `require-dbt-version` is `<3.0.0`. The 1.1.0 pinned in
`azure_fabric` and `databricks` caps at `<2.0.0`, so `dbt deps` refuses to
install it under dbt 2.x.

`stg_orders_pkg` calls `dbt_utils.generate_surrogate_key`, so a run proves the
package resolved *and* that its macros execute on this dbt version — a
`dbt deps` alone only proves the download.

## Running it

```bash
cd dbt_projects/bigquery_packages
dbt deps          # package install only, no warehouse needed
dbt build         # needs the BigQuery connection
```

## In Orchestra

Point a dbt Core task at `project_dir: dbt_projects/bigquery_packages` with the
connection above. To run it against an unreleased build of the state-aware
orchestration package, set the task's environment variables to:

```json
{"ORCHESTRA_DBT_BRANCH": "<branch of orchestra-hq/sao-paolo>"}
```

The runner installs `dbt-orchestra` from that branch instead of the pinned
release. It is a development switch, not production configuration.
