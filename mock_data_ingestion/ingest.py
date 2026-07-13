"""Mock data ingestion job.

Generates synthetic customer + order records and loads them into a local
SQLite database (analytics.db). Intended as a lightweight, dependency-free
example of an ingestion step that can be orchestrated by Orchestra.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import date, timedelta

DB_PATH = os.environ.get("INGEST_DB_PATH", "analytics.db")

# --- Deterministic mock source data -------------------------------------------------
CUSTOMERS = [
    (1, "Acme Corp", "enterprise", "US"),
    (2, "Globex", "mid-market", "GB"),
    (3, "Initech", "smb", "US"),
    (4, "Umbrella Ltd", "enterprise", "DE"),
    (5, "Hooli", "mid-market", "US"),
]

# (order_id, customer_id, days_ago, amount_usd, status)
ORDERS = [
    (1001, 1, 1, 12500.00, "paid"),
    (1002, 2, 2, 3200.50, "paid"),
    (1003, 3, 3, 450.00, "pending"),
    (1004, 1, 5, 8800.00, "paid"),
    (1005, 4, 6, 21000.00, "paid"),
    (1006, 5, 7, 1750.25, "refunded"),
    (1007, 2, 9, 990.00, "pending"),
    (1008, 4, 10, 15600.00, "paid"),
]


def build_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP TABLE IF EXISTS orders;
        DROP TABLE IF EXISTS customers;

        CREATE TABLE customers (
            customer_id   INTEGER PRIMARY KEY,
            name          TEXT    NOT NULL,
            segment       TEXT    NOT NULL,
            country       TEXT    NOT NULL
        );

        CREATE TABLE orders (
            order_id     INTEGER PRIMARY KEY,
            customer_id  INTEGER NOT NULL REFERENCES customers(customer_id),
            order_date   TEXT    NOT NULL,
            amount_usd   REAL    NOT NULL,
            status       TEXT    NOT NULL,
            loaded_at    TEXT    NOT NULL
        );
        """
    )


def ingest(conn: sqlite3.Connection) -> None:
    today = date(2026, 7, 13)  # fixed for reproducible runs
    loaded_at = "2026-07-13T00:00:00Z"

    conn.executemany(
        "INSERT INTO customers (customer_id, name, segment, country) VALUES (?, ?, ?, ?)",
        CUSTOMERS,
    )

    rows = [
        (
            oid,
            cid,
            (today - timedelta(days=days_ago)).isoformat(),
            amount,
            status,
            loaded_at,
        )
        for (oid, cid, days_ago, amount, status) in ORDERS
    ]
    conn.executemany(
        "INSERT INTO orders (order_id, customer_id, order_date, amount_usd, status, loaded_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()


def summarise(conn: sqlite3.Connection) -> None:
    n_customers = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    n_orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    revenue = conn.execute(
        "SELECT ROUND(SUM(amount_usd), 2) FROM orders WHERE status = 'paid'"
    ).fetchone()[0]

    print(f"[ingest] database: {DB_PATH}")
    print(f"[ingest] customers loaded: {n_customers}")
    print(f"[ingest] orders loaded:    {n_orders}")
    print(f"[ingest] paid revenue USD: {revenue}")
    print("[ingest] done.")


def main() -> None:
    print(f"[ingest] starting mock ingestion into {DB_PATH} ...")
    conn = sqlite3.connect(DB_PATH)
    try:
        build_schema(conn)
        ingest(conn)
        summarise(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
