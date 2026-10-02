"""Dummy extract step for the end-to-end blueprint.

Generates a deterministic batch of fake orders, writes them where the dbt
project can pick them up, and publishes the batch size back to Orchestra as a
Task output. The dbt Task downstream reads that output as a dbt var, so the two
halves of the pipeline are wired together rather than merely ordered.

Nothing here talks to a real source system: the point is a runnable shape, not
a real extract.
"""

import os
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from orchestra_sdk.orchestra import OrchestraSDK

# Deterministic by default so repeated runs build a stable duration baseline.
SEED = int(os.getenv("DUMMY_SEED", "42"))
ROW_COUNT = int(os.getenv("DUMMY_ROW_COUNT", "500"))
OUTPUT_PATH = Path(os.getenv("DUMMY_OUTPUT_PATH", "dummy_orders.csv"))

STATUSES = ("completed", "pending", "returned")


def build_rows(row_count: int, seed: int) -> list[dict]:
    """Generate `row_count` fake orders."""
    rng = random.Random(seed)
    today = datetime.now(timezone.utc).date()
    return [
        {
            "order_id": i,
            "customer_id": rng.randint(100, 149),
            "order_date": (today - timedelta(days=rng.randint(0, 29))).isoformat(),
            "status": rng.choice(STATUSES),
            "amount": round(rng.uniform(5, 500), 2),
        }
        for i in range(1, row_count + 1)
    ]


def write_csv(rows: list[dict], path: Path) -> None:
    """Write the batch out as CSV, headers included."""
    path.parent.mkdir(parents=True, exist_ok=True)
    header = ",".join(rows[0].keys())
    body = "\n".join(",".join(str(value) for value in row.values()) for row in rows)
    path.write_text(f"{header}\n{body}\n")


def main() -> None:
    rows = build_rows(ROW_COUNT, SEED)
    write_csv(rows, OUTPUT_PATH)
    print(f"Extracted {len(rows)} dummy orders to {OUTPUT_PATH}")

    # Published so the dbt Task can consume it as a dbt var. Orchestra Task
    # outputs are only readable by another Task in the same pipeline.
    orchestra = OrchestraSDK(api_key=os.environ["ORCHESTRA_API_KEY"])
    orchestra.set_output(name="row_count", value=str(len(rows)))
    print("Set Orchestra output 'row_count'")


if __name__ == "__main__":
    main()
