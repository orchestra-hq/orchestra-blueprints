# Warehouse Savings Analysis

Total Operation Duration Analysis for Orchestra dbt Core Operations. This script visualizes the total duration of all operations per task run, specifically those using stateful orchestration.

## Usage

Install dependencies:

```bash
pip install -r requirements.txt
```

Set the `ORCHESTRA_API_KEY` environment variable and run:

```bash
python graph.py
```

## Configuration

Key constants in `graph.py`:

- `DEFAULT_ANALYSIS_DAYS`: Time range for analysis (default: 30)
- `FIGURE_WIDTH`, `FIGURE_HEIGHT`: Plot dimensions
- `COLOR_PALETTE`: Line colors for different tasks
