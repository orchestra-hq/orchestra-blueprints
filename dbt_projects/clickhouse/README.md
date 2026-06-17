# dbt-orchestra-metadata-clickhouse

A minimal ClickHouse-based dbt project demonstrating Orchestra metadata integration.

## Overview

This is a sample dbt project configured for ClickHouse that demonstrates basic setup and integration with Orchestra platform metadata.

## Setup

### Requirements

- dbt >= 1.5
- dbt-clickhouse adapter
- ClickHouse database (local or remote)
- Python 3.9+ (for development)

### Installation

1. Clone the repository

2. Install dependencies using uv (recommended):
```bash
uv sync
```

Or with pip:
```bash
pip install -r requirements.txt
```

3. Configure your ClickHouse connection in `profiles.yml`:
```yaml
orchestra_metadata_clickhouse:
  target: dev
  outputs:
    dev:
      type: clickhouse
      host: localhost
      port: 8123
      user: default
      password: ""
      database: default
      schema: orchestra
      threads: 4
```

4. Run dbt:
```bash
uv run dbt debug
uv run dbt build
```

## Project Structure

```
.
├── models/
│   ├── integration_testing_data.sql  # Sample model
│   └── schema.yml                     # Model definitions
├── sources/
│   └── sources.yml                   # Source definitions
├── dbt_project.yml                   # Project configuration
├── profiles.yml                      # Connection configuration
├── pyproject.toml                    # Python dependencies
└── README.md
```


## Configuration

Variables can be set in `dbt_project.yml` or via command line:

```yaml
vars:
  orchestra_source_schema: 'orchestra'  # Schema containing Orchestra source tables
  orchestra_source_database: null       # Database name (if using multi-db setup)
```

## Development

### Running Models

```bash
uv run dbt run
```

### Testing

```bash
uv run dbt test
```

### Documentation

Generate dbt docs:
```bash
uv run dbt docs generate
uv run dbt docs serve
```

## Support

For issues or questions, please refer to:
- [dbt Documentation](https://docs.getdbt.com/)
- [dbt-clickhouse Adapter](https://github.com/ClickHouse/dbt-clickhouse)
- [Orchestra Documentation](https://docs.getorchestra.io/)
