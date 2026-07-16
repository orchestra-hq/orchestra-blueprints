# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "snowflake-connector-python",
#     "pandas",
#     "orchestra-sdk",
# ]
# ///
"""
ingest_raw_data.py
------------------
Python ingest step for the "ELT — Python -> dbt/Snowflake (MetaEngine) -> Power BI"
pipeline.

1. Loads raw sample data into Snowflake (additive: CREATE TABLE IF NOT EXISTS + INSERT).
2. Emits an Orchestra task output named ``output`` that drives the downstream
   MetaEngine matrix. The transform group fans out with
   ``dbt build --select ${{ matrix.domain.selector }}``, so each item must expose
   a ``selector`` key.

Required environment variables (Snowflake):
  SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD,
  SNOWFLAKE_DATABASE, SNOWFLAKE_WAREHOUSE
Optional: SNOWFLAKE_SCHEMA (default PUBLIC), SNOWFLAKE_ROLE
Injected by Orchestra when "Set outputs" is enabled: ORCHESTRA_API_KEY
"""

import os
import sys
import logging

import pandas as pd
import snowflake.connector

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# dbt selection domains for the downstream MetaEngine matrix.
# These map to model sub-directories in dbt_projects/snowflake and are consumed as
# `dbt build --select <selector>`.
DBT_DOMAINS = [
    {"name": "staging", "selector": "staging"},
    {"name": "clean", "selector": "clean"},
    {"name": "aggregated", "selector": "aggregated"},
    {"name": "production", "selector": "production"},
]


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
    # Additive only: never drops or recreates existing data.
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS orchestra_ingest_demo (
            id          NUMBER AUTOINCREMENT PRIMARY KEY,
            source      VARCHAR(255),
            event_ts    TIMESTAMP_NTZ,
            payload     VARIANT,
            loaded_at   TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        )
        """
    )
    logger.info("Table orchestra_ingest_demo ensured.")


def load_sample_data(cur):
    sample = pd.DataFrame(
        [
            {
                "source": "orchestra_pipeline",
                "event_ts": pd.Timestamp.utcnow().isoformat(),
                "payload": '{"status": "ok"}',
            }
        ]
    )
    rows = list(sample.itertuples(index=False, name=None))
    cur.executemany(
        "INSERT INTO orchestra_ingest_demo (source, event_ts, payload) "
        "SELECT %s, %s, PARSE_JSON(%s)",
        rows,
    )
    logger.info("Inserted %d row(s).", len(rows))


def set_matrix_output():
    """Publish the domain list for the downstream MetaEngine dbt matrix."""
    api_key = os.environ.get("ORCHESTRA_API_KEY")
    if not api_key:
        logger.warning("ORCHESTRA_API_KEY not set; skipping set_output (matrix will be empty).")
        return
    try:
        from orchestra_sdk.orchestra import OrchestraSDK

        orchestra = OrchestraSDK(api_key=api_key)
        orchestra.set_output(name="output", value=DBT_DOMAINS)
        logger.info("Set output 'output' with %d domain(s): %s", len(DBT_DOMAINS), DBT_DOMAINS)
    except Exception:
        logger.exception("Failed to set Orchestra output")
        raise


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

    set_matrix_output()


if __name__ == "__main__":
    main()
