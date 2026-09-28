# Reusable Patterns

This directory contains reusable blueprint patterns for working with Orchestra.

Unlike most `python/` subfolders (which are intended to be executed by Orchestra as
task modules), these examples are designed to interact with Orchestra as a
platform via Orchestra APIs.

## Subdirectories

- `run_multiple_pipelines/`: examples for programmatic multi-pipeline runs.
- `warehouse_savings/`: warehouse optimization and analytics pattern examples.
- `duckdb_quality/`: declarative data quality tests against Snowflake, run
  through the DuckDB CLI. Unlike the patterns above this one talks to the
  warehouse directly rather than to the Orchestra API.

