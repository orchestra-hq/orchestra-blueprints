"""Print daily order totals and the grand total."""
import csv
from collections import defaultdict
from pathlib import Path


def load_orders(path):
    with open(path) as f:
        rows = list(csv.DictReader(f))
    return rows[1:]


def main():
    totals = defaultdict(float)
    for row in load_orders(Path(__file__).with_name("orders.csv")):
        totals[row["order_date"]] += float(row["amount"])
    for day, total in sorted(totals.items()):
        print(f"{day}: {total:.2f}")
    print(f"grand_total: {sum(totals.values()):.2f}")


if __name__ == "__main__":
    main()
