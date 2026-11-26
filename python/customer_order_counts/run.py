"""Load the CSVs into SQLite and run customer_order_counts.sql."""
import csv
import sqlite3
from pathlib import Path

HERE = Path(__file__).parent


def main():
    con = sqlite3.connect(":memory:")
    for name in ("customers", "orders", "addresses"):
        with open(HERE / f"{name}.csv") as f:
            rows = list(csv.reader(f))
        cols = ", ".join(rows[0])
        con.execute(f"create table {name} ({cols})")
        con.executemany(f"insert into {name} values ({', '.join('?' * len(rows[0]))})", rows[1:])
    cur = con.execute((HERE / "customer_order_counts.sql").read_text())
    print(",".join(d[0] for d in cur.description))
    for row in cur:
        print(",".join(str(v) for v in row))


if __name__ == "__main__":
    main()
