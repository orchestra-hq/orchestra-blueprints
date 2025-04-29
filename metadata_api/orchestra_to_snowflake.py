import os
import sys

import snowflake.connector

from metadata_api.common import (
    COLUMNS,
    VALID_RESOURCES,
    fetch_data_from_api,
    parse_record_values,
)


def insert_data_into_snowflake(data: list[dict], resource: str):
    conn = snowflake.connector.connect(
        account=os.environ.get("SNOWFLAKE_ACCOUNT"),
        user=os.environ.get("SNOWFLAKE_USER"),
        password=os.environ.get("SNOWFLAKE_PASSWORD"),
        database=os.environ.get("SNOWFLAKE_DATABASE"),
        schema=os.environ.get("SNOWFLAKE_SCHEMA"),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE"),
    )
    cursor = conn.cursor()

    try:
        for record in data:
            placeholders = ", ".join(["%s"] * len(COLUMNS[resource]))
            columns = ", ".join(COLUMNS[resource])
            sql = f"INSERT INTO {resource} ({columns}) VALUES ({placeholders})"
            cursor.execute(sql, parse_record_values(list(record.values()), resource))
        conn.commit()
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python orchestra_to_snowflake.py <{'|'.join(VALID_RESOURCES)}>")
        exit(1)

    resource = sys.argv[1].lower()
    if resource not in VALID_RESOURCES:
        print(
            f"Invalid resource '{resource}'. Valid resources are: {', '.join(VALID_RESOURCES)}"
        )
        exit(2)

    insert_data_into_snowflake(
        fetch_data_from_api(resource=resource), resource=resource
    )
