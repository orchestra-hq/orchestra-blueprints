import os
import sys
from google.cloud import bigquery
from google.oauth2 import service_account
from metadata_api.common import (
    VALID_RESOURCES,
    fetch_data_from_api,
    parse_record_values,
)


def insert_data_into_bigquery(data: list[dict], resource: str):
    client = bigquery.Client(
        project=os.environ.get("GCP_PROJECT_ID"),
        credentials=service_account.Credentials.from_service_account_info(
            info=os.environ.get("GCP_SERVICE_ACCOUNT_JSON"),
            scopes=["https://www.googleapis.com/auth/bigquery"],
        ),
    )
    table_id = (
        f"{os.environ.get('GCP_PROJECT_ID')}.{os.environ.get('GCP_DATASET')}.{resource}"
    )

    try:
        errors = client.insert_rows_json(table_id, parse_record_values(data, resource))
        if errors:
            print("Errors occurred while inserting rows:", errors)
        else:
            print("Data successfully inserted into BigQuery.")
    finally:
        client.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python orchestra_to_big_query.py <{'|'.join(VALID_RESOURCES)}>")
        exit(1)

    resource = sys.argv[1].lower()
    if resource not in VALID_RESOURCES:
        print(
            f"Invalid resource '{resource}'. Valid resources are: {', '.join(VALID_RESOURCES)}"
        )
        exit(2)

    insert_data_into_bigquery(fetch_data_from_api(resource=resource), resource=resource)
