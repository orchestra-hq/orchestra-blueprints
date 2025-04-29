import os
import requests
from google.cloud import bigquery

# Orchestra Metadata API Configuration
API_TOKEN = os.environ.get("ORCHESTRA_API_TOKEN")
API_URL = "https://app.getorchestra.io/api/engine/public/{resource}/"
API_HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}

# BigQuery Configuration
BIGQUERY_PROJECT_ID = "your-project-id"  # Replace with your GCP project ID
BIGQUERY_DATASET = "your_dataset"        # Replace with your BigQuery dataset name
BIGQUERY_TABLE = "your_table"            # Replace with your BigQuery table name

def fetch_data_from_api(resource: str):
    response = requests.get(API_URL.format(resource=resource), headers=API_HEADERS)
    response.raise_for_status()
    return response.json()

def insert_data_into_bigquery(data):
    client = bigquery.Client(project=BIGQUERY_PROJECT_ID)
    table_id = f"{BIGQUERY_PROJECT_ID}.{BIGQUERY_DATASET}.{BIGQUERY_TABLE}"
    
    # Convert data to BigQuery-compatible format
    rows_to_insert = [
        {
            "column1": item["key1"],  # Replace with your actual column mappings
            "column2": item["key2"],  # Replace with your actual column mappings
        }
        for item in data
    ]
    
    # Insert rows into BigQuery
    errors = client.insert_rows_json(table_id, rows_to_insert)
    if errors:
        print("Errors occurred while inserting rows:", errors)
    else:
        print("Data successfully inserted into BigQuery.")

def main(resource: str):
    data = fetch_data_from_api(resource=resource)
    if isinstance(data, list):  # Ensure data is a list of records
        insert_data_into_bigquery(data)
    else:
        print(f"Unexpected data format from API: {type(data)}")

if __name__ == "__main__":
    main("pipeline_runs")