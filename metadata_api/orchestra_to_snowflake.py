import os
import requests

import snowflake.connector

# Orchestra Metadata API Configuration
API_TOKEN = os.environ.get("ORCHESTRA_API_TOKEN")
API_URL = "https://app.getorchestra.io/api/engine/public/{RESOURCE}/"
API_HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}

# Snowflake Configuration
SNOWFLAKE_ACCOUNT = "your_account"
SNOWFLAKE_USER = "your_user"
SNOWFLAKE_PASSWORD = "your_password"
SNOWFLAKE_DATABASE = "your_database"
SNOWFLAKE_SCHEMA = "your_schema"
SNOWFLAKE_WAREHOUSE = "your_warehouse"
SNOWFLAKE_TABLE = "your_table"


def fetch_data_from_api(resource: str):
    response = requests.get(API_URL.format(resource=resource), headers=API_HEADERS)
    response.raise_for_status()
    return response.json()


def insert_data_into_snowflake(data):
    # Establish Snowflake connection
    conn = snowflake.connector.connect(
        account=SNOWFLAKE_ACCOUNT,
        user=SNOWFLAKE_USER,
        password=SNOWFLAKE_PASSWORD,
        database=SNOWFLAKE_DATABASE,
        schema=SNOWFLAKE_SCHEMA,
        warehouse=SNOWFLAKE_WAREHOUSE,
    )
    cursor = conn.cursor()

    # Insert data into Snowflake table
    try:
        for record in data:
            placeholders = ", ".join(["%s"] * len(record))
            columns = ", ".join(record.keys())
            sql = f"INSERT INTO {SNOWFLAKE_TABLE} ({columns}) VALUES ({placeholders})"
            cursor.execute(sql, list(record.values()))
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def main(resource: str):
    data = fetch_data_from_api(resource=resource)
    if isinstance(data, list):  # Ensure data is a list of records
        insert_data_into_snowflake(data)
    else:
        print(f"Unexpected data format from API: {type(data)}")


if __name__ == "__main__":
    main("pipeline_runs")
