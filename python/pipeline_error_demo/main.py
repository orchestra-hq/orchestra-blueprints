import sys

print("Starting data pipeline...")
rows_expected = 100
rows_loaded = 0
print(f"Rows expected: {rows_expected}, rows loaded: {rows_loaded}")

# Simulate a data pipeline failure
if rows_loaded < rows_expected:
    raise RuntimeError(
        f"Data quality check failed: loaded {rows_loaded} rows, expected {rows_expected}."
    )

print("Pipeline completed successfully")
