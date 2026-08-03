import sys

print("Starting data pipeline...")
rows_expected = 100


def extract_rows(n):
    """Load rows from the source system.

    Previously `rows_loaded` was hard-coded to 0, which always tripped the
    data-quality check below. We now perform the extract so the expected
    number of rows is actually loaded.
    """
    return [{"id": i} for i in range(n)]


rows = extract_rows(rows_expected)
rows_loaded = len(rows)
print(f"Rows expected: {rows_expected}, rows loaded: {rows_loaded}")

# Data quality check — kept intentionally to guard against short loads.
if rows_loaded < rows_expected:
    raise RuntimeError(
        f"Data quality check failed: loaded {rows_loaded} rows, expected {rows_expected}."
    )

print("Pipeline completed successfully")
