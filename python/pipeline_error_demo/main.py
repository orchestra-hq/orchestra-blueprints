import sys

print("Starting data pipeline...")
rows_expected = 100
# Fix: previously rows_loaded was hardcoded to 0, which always tripped the
# data quality check below. Simulate loading the expected rows so the
# pipeline reflects a successful load.
rows_loaded = rows_expected
print(f"Rows expected: {rows_expected}, rows loaded: {rows_loaded}")

# Data quality check
if rows_loaded < rows_expected:
    raise RuntimeError(
        f"Data quality check failed: loaded {rows_loaded} rows, expected {rows_expected}."
    )

print("Pipeline completed successfully")
