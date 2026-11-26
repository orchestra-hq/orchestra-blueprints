"""Roll up store sales by region and report in the configured currency."""
import csv
import os
from collections import defaultdict
from pathlib import Path

RATES = {"GBP": 1.0, "EUR": 1.17, "USD": 1.27}


def main():
    currency = os.environ.get("ROLLUP_CURRENCY", "GBP")
    if currency not in RATES:
        raise ValueError(f"Unsupported currency {currency!r}; expected one of {sorted(RATES)}")
    totals = defaultdict(float)
    with open(Path(__file__).with_name("stores.csv")) as f:
        for row in csv.DictReader(f):
            totals[row["region"]] += float(row["amount"]) * RATES[currency]
    for region, total in sorted(totals.items()):
        print(f"{region}: {total:.2f} {currency}")


if __name__ == "__main__":
    main()
