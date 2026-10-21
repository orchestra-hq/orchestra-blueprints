# bigquery_sao_v2_edge

A BigQuery project on dbt v2 (`dbt-oss`) for testing `dbt-orchestra` (`orc`)
against the node kinds its `dbt ls` → manifest mapping has to handle:

| Node | fqn |
| --- | --- |
| seed `edge_seed` | `sao_v2_edge.edge_seed` |
| root model `stg_edge` | `sao_v2_edge.stg_edge` |
| singular test `tests/stg_edge.sql` | `sao_v2_edge.stg_edge` (same as the model) |
| versioned model `dim_edge` v1, v2 | `sao_v2_edge.marts.dim_edge.v1` / `.v2` |
| package model `pkg_edge` (local package `edge_pkg`) | `edge_pkg.pkg_edge` |
| snapshot `snap_edge` | `sao_v2_edge.snap_edge` |

There are no sources, so reuse is driven by checksums alone: run with
`ORCHESTRA_SEED_STATE_ORCHESTRATION=true` or the seed (and everything below
it) always rebuilds. Snapshots always rebuild. `selectors.yml` has one
selector, `edge_marts` (`models/marts`).

`profiles_duckdb/` is a credential-free profile (DuckDB `dev` and `alt`
targets) for exercising `--profiles-dir` and `--target`; it is force-added
past the repo's `profiles.yml` ignore rule.

Everything lands in the `dbt_sao_v2_edge` dataset, separate from
`dbt_sao_demo`, so this project's SAO state never mixes with the `bigquery`
project's. `macros/log_target.sql` logs the active target without secrets
(`dbt run-operation log_target`).
