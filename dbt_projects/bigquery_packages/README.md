# bigquery_packages

The `bigquery` blueprint restructured so that **the root project owns no models
at all** — every model and every source belongs to the installed `orders_pkg`
package. It exists so a dbt Core task can exercise `dbt deps` and a
package-owned DAG against real sources without touching any production dataset.

This is the shape that breaks source-freshness scoping: `dbt ls --output path`
reports a node's `original_file_path` relative to the package that owns it
(`models/staging/stg_orders_pkg.sql`), but the file actually sits at
`dbt_packages/orders_pkg/models/staging/stg_orders_pkg.sql`, so a
`--select +path:...` criterion globs from the project root, matches nothing, and
silently selects zero nodes.

- **dbt version:** dbt-core 1.12.5 / dbt-bigquery 1.12.1 — the latest 1.x.
  State-aware orchestration is fully functional here; on dbt 2.x it silently
  does nothing (see below).
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
  (table), all owned by `orders_pkg`.

## The packages

Two, for different reasons:

- **`orders_pkg`** (`vendor/orders_pkg`, installed as a `local:` package) holds
  the entire DAG — both models, both sources. `models/` in the root project is
  empty and must stay that way; a model added there stops this being a
  package-only project.
- **`dbt-labs/dbt_utils`** at **1.4.1** supplies a macro to call. 1.4.1 rather
  than the 1.1.0 pinned in `azure_fabric` and `databricks`: that release caps
  `require-dbt-version` at `<2.0.0`, so it cannot follow this project onto
  dbt 2.x later.

`stg_orders_pkg` calls `dbt_utils.generate_surrogate_key`, so a run proves the
package resolved *and* that its macros execute on this dbt version — a
`dbt deps` alone only proves the download.

## What a dbt 2.x run showed

Both were confirmed on dbt 2.0.4 with `dbt-orchestra` 1.4.0, and are why this
project sits on 1.x:

1. `loaded_at_field` and `freshness` must be nested under `config:` on a source.
   At source level dbt 2.x raises `UnusedConfigKey (dbt1060)` and the build
   fails. This project already uses the nested shape, which 1.10+ accepts too.
2. State-aware orchestration is inert. dbt 2.x writes a `sources/v3`
   `sources.json` whose `criteria` object omits `loaded_at_field` /
   `loaded_at_query`, so `dbt-orchestra` treats every source as having no
   explicit freshness and excludes it — even though `max_loaded_at` in the same
   file is correct. Every run reuses 0 nodes.

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
