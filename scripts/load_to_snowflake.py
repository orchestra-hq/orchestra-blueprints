"""
load_to_snowflake.py
--------------------
Loads sample/staged data into Snowflake.

Credentials can come from an Orchestra linked Snowflake connection
(SNOWFLAKE__<CONNECTION_ID>__SNOWFLAKE_*); explicit variables below win.

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


def apply_linked_connection_env():
    """Fill missing SNOWFLAKE_* variables from an Orchestra linked Snowflake connection.

    Orchestra exports linked connection credentials as
    SNOWFLAKE__<CONNECTION_ID>__SNOWFLAKE_<FIELD>. Set SNOWFLAKE_CONNECTION_ID
    to choose one when several Snowflake connections are linked.
    """
    wanted = os.environ.get("SNOWFLAKE_CONNECTION_ID", "").upper()
    prefixes = sorted(
        {
            k.rsplit("__", 1)[0] + "__"
            for k in os.environ
            if k.startswith("SNOWFLAKE__") and k.count("__") == 2
        }
    )
    if wanted:
        prefixes = [p for p in prefixes if p == f"SNOWFLAKE__{wanted}__"]
    if not prefixes:
        return
    prefix = prefixes[0]
    for field in ["ACCOUNT", "USER", "PASSWORD", "DATABASE", "SCHEMA", "WAREHOUSE", "ROLE"]:
        name = f"SNOWFLAKE_{field}"
        linked = os.environ.get(f"{prefix}{name}")
        if linked and not os.environ.get(name):
            os.environ[name] = linked
    logger.info("Using linked Snowflake connection %s", prefix.strip("_"))


def get_snowflake_connection():
    apply_linked_connection_env()
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
