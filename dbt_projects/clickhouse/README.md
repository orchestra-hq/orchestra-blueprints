# dbt-orchestra-metadata-clickhouse

A ClickHouse-based dbt project that transforms Orchestra platform metadata into an analytics-ready dimensional model.

## Overview

This dbt project processes execution metadata from the Orchestra API (ingested via dlt) to provide insights into:

- **Pipeline Observability**: Monitor success rates, failures, execution durations
- **Integration Performance**: Compare performance across different integration types
- **Data Lineage**: Map upstream/downstream asset dependencies
- **Operational Metrics**: Build dashboards and SLA reports
- **Resource Optimization**: Identify long-running operations and bottlenecks

## Data Sources

The project works with four main data streams from Orchestra:

- **Pipeline Runs**: Pipeline execution metadata including status, timing, and git context
- **Task Runs**: Individual task executions within pipelines with integration details
- **Operations**: Granular operation-level details (rows affected, duration, type)
- **Assets**: Data asset catalog with upstream/downstream dependencies

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
│   ├── staging/          # Cleaned and renamed source data
│   │   ├── stg_orchestra__pipeline_runs.sql
│   │   ├── stg_orchestra__task_runs.sql
│   │   ├── stg_orchestra__operations.sql
│   │   ├── stg_orchestra__assets.sql
│   │   └── schema.yml
│   └── marts/            # Analytics-ready tables
│       ├── dimensions/   # Reference tables (pipelines, integrations, assets)
│       └── facts/        # Event tables (pipeline runs, task runs, operations)
├── macros/               # Custom dbt macros
├── tests/                # dbt tests
├── dbt_project.yml       # Project configuration
├── profiles.yml          # Connection configuration
├── packages.yml          # dbt package dependencies
└── README.md
```

## Data Model

### Staging Layer

Staging models clean and standardize raw source data:

- `stg_orchestra__pipeline_runs` - Renamed columns, calculated durations, status flags
- `stg_orchestra__task_runs` - Enriched task data with pipeline references
- `stg_orchestra__operations` - Operation details with categorization flags
- `stg_orchestra__assets` - Asset metadata with dependency counts

### Marts Layer

#### Dimensions (Reference Tables)

- **dim_pipelines**: Pipeline definitions with aggregated execution statistics
- **dim_integrations**: Integration types and jobs with performance metrics
- **dim_assets**: Data asset catalog with classifications and dependencies

#### Facts (Event Tables)

- **fct_pipeline_runs**: Pipeline execution events with task rollups
- **fct_task_runs**: Task execution events with operation rollups
- **fct_operations**: Granular operation events with throughput metrics

## Key Features

### ClickHouse Optimizations

- Uses `ReplacingMergeTree` engine for fact tables with soft deletes via version column
- Partitioning by year-month for efficient queries and data management
- Order keys optimized for common query patterns
- Date keys for dimensional analysis

### Calculated Metrics

- Success/failure rates and percentages
- Duration metrics (seconds and minutes)
- Throughput calculations (rows per second)
- Task and operation aggregations

### Status Flags

Boolean flags for easy filtering:
- `is_successful`, `is_failed`, `is_cancelled`, `is_skipped`
- `has_warning`, `is_in_progress`
- Operation type flags (ingestion, transformation, testing, deployment)

## Usage Examples

### Pipeline Health Dashboard
```sql
select
    pipeline_name,
    created_date,
    total_tasks,
    successful_tasks,
    task_success_rate_pct,
    duration_minutes
from {{ ref('fct_pipeline_runs') }}
where created_date >= today() - 7
order by created_date desc
```

### Integration Performance Comparison
```sql
select
    integration,
    integration_job,
    task_success_rate_pct,
    total_rows_affected,
    avg_rows_affected
from {{ ref('dim_integrations') }}
order by task_success_rate_pct
```

### Asset Dependency Analysis
```sql
select
    asset_name,
    asset_type,
    upstream_dependency_count,
    downstream_dependency_count,
    size_gb
from {{ ref('dim_assets') }}
where is_database_object
order by size_gb desc
```

## Configuration

### Variables

Key variables can be set in `dbt_project.yml` or via command line:

```yaml
vars:
  orchestra_source_schema: 'orchestra'  # Schema containing Orchestra source tables
  orchestra_source_database: null       # Database name (if using multi-db)
  run_dbt_project_evaluator: false      # Enable dbt project evaluator
```

## Development

### Testing

```bash
uv run dbt test
```

### Linting

```bash
uv run sqlfluff lint models
```

### Documentation

Generate dbt docs:
```bash
uv run dbt docs generate
uv run dbt docs serve
```

## Performance Considerations

- Fact tables use `ReplacingMergeTree` for efficient updates
- Partitioning by `toYYYYMM(created_at_utc)` keeps partitions manageable
- Order keys support common filter patterns (date, integration type)
- Consider setting up TTL policies for data retention

## Support

For issues or questions, please refer to:
- [dbt Documentation](https://docs.getdbt.com/)
- [dbt-clickhouse Adapter](https://github.com/ClickHouse/dbt-clickhouse)
- [Orchestra Documentation](https://docs.getorchestra.io/)
