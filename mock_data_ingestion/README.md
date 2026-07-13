# Mock Data Ingestion Demo

A dependency-free example ingestion job used to demonstrate orchestrating
Python with Orchestra.

`ingest.py` generates synthetic customer + order records and loads them into a
local SQLite database (`analytics.db`), then prints a summary.

Run locally:

```bash
python mock_data_ingestion/ingest.py
```

Optional env var: `INGEST_DB_PATH` (default `analytics.db`).

This is executed by the Orchestra pipeline **Mock Data Ingestion Demo** via a
Python (Git) task on branch `mock-data-ingestion-demo`.
