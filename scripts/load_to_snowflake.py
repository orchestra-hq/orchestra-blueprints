"""
load_to_snowflake.py
--------------------
Loads sample/staged data into Snowflake.

Required environment variables:
  SNOWFLAKE_ACCOUNT    - e.g. xy12345.us-east-1
  SNOWFLAKE_USER       - Snowflake username
  SNOWFLAKE_PASSWORD   - Snowflake password
  SNOWFLAKE_DATABASE   - Target database
  SNOWFLAKE_SCHEMA     - Target schema (default: PUBLIC)
  SNOWFLAKE_WAREHOUSE  - Warehouse name
  SNOWFLAKE_ROLE       - (optional) Role to use
"""

import os
import sys
import logging
import snowflake.connector
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def get_snowflake_connection():
    required = [
        "SNOWFLAKE_ACCOUNT",
        "SNOWFLAKE_USER",
        "SNOWFLAKE_PASSWORD",
        "SNOWFLAKE_DATABASE",
        "SNOWFLAKE_WAREHOUSE",
    ]
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        logger.error("Missing required environment variables: %s", missing)
        sys.exit(1)

    conn_kwargs = dict(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        database=os.environ["SNOWFLAKE_DATABASE"],
        schema=os.environ.get("SNOWFLAKE_SCHEMA", "PUBLIC"),
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
    )
    if os.environ.get("SNOWFLAKE_ROLE"):
        conn_kwargs["role"] = os.environ["SNOWFLAKE_ROLE"]

    return snowflake.connector.connect(**conn_kwargs)


def ensure_table(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orchestra_ingest_demo (
            id          NUMBER AUTOINCREMENT PRIMARY KEY,
            source      VARCHAR(255),
            event_ts    TIMESTAMP_NTZ,
            payload     VARIANT,
            loaded_at   TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        )
    """)
    logger.info("Table orchestra_ingest_demo ensured.")


def load_sample_data(cur):
    sample = pd.DataFrame(
        [
            {
                "source": "orchestra_pipeline",
                "event_ts": pd.Timestamp.utcnow().isoformat(),
                "payload": '{"status": "ok"}',
            },
        ]
    )
    rows = list(sample.itertuples(index=False, name=None))
    cur.executemany(
        "INSERT INTO orchestra_ingest_demo (source, event_ts, payload) SELECT %s, %s, PARSE_JSON(%s)",
        rows,
    )
    logger.info("Inserted %d row(s).", len(rows))


def main():
    logger.info("Connecting to Snowflake...")
    conn = get_snowflake_connection()
    try:
        with conn.cursor() as cur:
            ensure_table(cur)
            load_sample_data(cur)
        conn.commit()
        logger.info("Load complete.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
