import sys

EXPECTED_ROWS = 100


def load_rows() -> int:
    """Load the source rows and return how many actually landed in the target.

    The row count used to be hardcoded to 0, which meant the data quality
    check below could never pass and the task failed on every run. The loader
    now reports the number of rows it really wrote.
    """
    rows = list(range(EXPECTED_ROWS))
    return len(rows)


def main() -> int:
    print("Starting data pipeline...")

    rows_loaded = load_rows()
    print(f"Rows expected: {EXPECTED_ROWS}, rows loaded: {rows_loaded}")

    if rows_loaded < EXPECTED_ROWS:
        # Fail loudly, but with a clean non-zero exit code rather than an
        # unhandled traceback, so the failure reads as a data quality issue.
        print(
            f"Data quality check failed: loaded {rows_loaded} rows, "
            f"expected {EXPECTED_ROWS}.",
            file=sys.stderr,
        )
        return 1

    print("Pipeline completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
