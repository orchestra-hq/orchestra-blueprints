# MotherDuck oil dbt project

This project mirrors the [orchestra-blueprints Snowflake dbt layout](https://github.com/orchestra-hq/orchestra-blueprints/tree/main/dbt_projects/snowflake) for the oil pipeline only:

- `models/clean/oil_data_clean.sql` — same logic as Snowflake; `_pk` uses `sha256` instead of `sha2_binary` for DuckDB.
- `models/aggregated/oil_data_aggregated.sql` — same SQL as the Snowflake model.
- `models/staging/oil_area_staging.sql` and `oil_production_staging.sql` — same structure as Snowflake; the Snowflake `customers_clean` anchor in the `base` CTE is replaced with `oil_data_clean` so the project does not depend on the full Snowflake DAG.

Upstream raw data is declared as `source('fivetran', 'oil_data')` under schema `google_sheets`. Load or sync `oil_data` into MotherDuck with that schema name (or adjust `sources/sources.yml`).

## Setup

Copy `profiles.yml.example` to `~/.dbt/profiles.yml` (merge the `motherduck` profile into your existing file) or pass `--profiles-dir` with a directory that contains `profiles.yml`. Use `type: duckdb` and a MotherDuck path such as `path: md:my_database` ([dbt-duckdb](https://github.com/dbt-labs/dbt-duckdb)).

From this directory, with `uv`:

```bash
uv sync
uv run dbt parse
uv run dbt run
```

Or install dependencies with `pip install duckdb==1.5.2 dbt-duckdb==1.10.1 dbt-core==1.10.9` and run `dbt` as usual.
