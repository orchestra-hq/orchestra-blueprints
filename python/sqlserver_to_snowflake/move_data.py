"""Dummy SQL Server -> Snowflake data movement script.

This is a SIMULATION for an Orchestra blueprint demo. It does NOT connect to
any real database. It mimics the shape of a typical extract-and-load job:

    SQL Server (source)  ->  staging  ->  Snowflake (target)

so the surrounding Orchestra pipeline (python -> dbt build -> dbt test) has a
realistic first step to trigger. Swap the simulated functions for real
`pyodbc` / `snowflake-connector-python` calls to make it live.
"""

import os
import time


SOURCE_TABLE = os.getenv("SOURCE_TABLE", "dbo.orders")
TARGET_TABLE = os.getenv("TARGET_TABLE", "RAW.ORDERS")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "500"))


def extract_from_sql_server(table: str):
    """Pretend to read rows from SQL Server."""
    print(f"[extract] connecting to SQL Server (simulated) ...")
    time.sleep(0.5)
    rows = [
        {"order_id": i, "customer": f"cust_{i % 7}", "amount": round(i * 1.25, 2)}
        for i in range(1, 1201)
    ]
    print(f"[extract] read {len(rows)} rows from {table}")
    return rows


def load_into_snowflake(rows, table: str, batch_size: int):
    """Pretend to bulk-load rows into Snowflake in batches."""
    print(f"[load] connecting to Snowflake (simulated) ...")
    time.sleep(0.5)
    loaded = 0
    for start in range(0, len(rows), batch_size):
        batch = rows[start:start + batch_size]
        loaded += len(batch)
        print(f"[load] staged batch {start // batch_size + 1}: {len(batch)} rows "
              f"({loaded}/{len(rows)})")
        time.sleep(0.2)
    print(f"[load] COPY INTO {table} complete: {loaded} rows")
    return loaded


def main():
    print("=== SQL Server -> Snowflake (simulated) ===")
    print(f"source={SOURCE_TABLE}  target={TARGET_TABLE}  batch_size={BATCH_SIZE}")
    rows = extract_from_sql_server(SOURCE_TABLE)
    loaded = load_into_snowflake(rows, TARGET_TABLE, BATCH_SIZE)
    assert loaded == len(rows), "row count mismatch between source and target"
    print(f"=== done: moved {loaded} rows SQL Server -> Snowflake ===")


if __name__ == "__main__":
    main()
