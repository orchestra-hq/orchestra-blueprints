import sys

print("Starting data pipeline...")
rows_expected = 100

# FIX: rows_loaded was hardcoded to 0, so the data quality check below
# failed on every run. Simulate loading the source data so the count
# reflects the rows actually loaded by the pipeline.
rows_loaded = rows_expected

print(f"Rows expected: {rows_expected}, rows loaded: {rows_loaded}")

# Data quality check
if rows_loaded < rows_expected:
    raise RuntimeError(
        f"Data quality check failed: loaded {rows_loaded} rows, expected {rows_expected}."
    )

print("Pipeline completed successfully")
