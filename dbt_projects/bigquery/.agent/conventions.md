# Conventions

Team-owned. Agents read this before proposing a fix.

- **Layers.** `staging/` is one view per source table: rename, cast, lower-case
  enums, nothing else. `marts/` are tables grouped to a stated grain.
- **Dataset.** Every model sets `+schema: dbt_sao_demo`; the
  `generate_schema_name` macro uses it verbatim. Never fall back to the
  connection's default dataset — the prod `core_*` datasets share the project.
- **Relation names.** A model's dbt name and its relation can differ via
  `alias` (`stg_orders` is `Stg Orders Clean`). Query by `ref()`, never by a
  hand-typed table name.
- **Types.** IDs are `int64`, money is `numeric`, dates are `date`.
- **Tests.** Every primary key gets `unique` + `not_null`. Every mart's grain
  column gets `unique`. Data-quality assertions that depend on business
  timing (staleness, late arrivals) are `severity: warn` unless the team says
  otherwise, and get an entry in `KNOWN_TEST_WARNINGS.yml` when triaged.
- **Sources are not ours.** Fix data problems upstream or in staging, never by
  writing to a source table.
