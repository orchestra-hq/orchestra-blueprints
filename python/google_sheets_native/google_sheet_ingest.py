import os

print(
    "DEBUG env keys:",
    sorted(
        k
        for k in os.environ
        if any(
            s in k.upper()
            for s in ["CRED", "GOOGLE", "GCP", "BIGQUERY", "SERVICE_ACCOUNT"]
        )
    ),
)

import google.auth
from google.cloud import bigquery
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/bigquery",
]


def run_google_sheets_ingest(
    spreadsheet_id: str,
    range_name: str,
    dataset_name: str,
    table_name: str,
) -> None:
    """Reads a range from a Google Sheet and loads it straight into BigQuery, no dlt involved."""
    credentials, project_id = google.auth.default(scopes=SCOPES)

    sheets_service = build("sheets", "v4", credentials=credentials)
    values = (
        sheets_service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=range_name)
        .execute()
        .get("values", [])
    )
    if not values:
        print(f"Range {range_name} returned no data. Nothing to load.")
        return

    headers, *rows = values
    records = [dict(zip(headers, row)) for row in rows]

    bq_client = bigquery.Client(credentials=credentials, project=project_id)
    table_id = f"{project_id}.{dataset_name}.{table_name}"
    job = bq_client.load_table_from_json(
        records,
        table_id,
        job_config=bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            autodetect=True,
        ),
    )
    job.result()
    print(f"Loaded {len(records)} rows into {table_id}")


run_google_sheets_ingest(
    os.environ["SHEET_NAME"],
    range_name=os.environ.get("RANGE_NAME", "dlt_range"),
    dataset_name=os.environ.get("DATASET_NAME", "sample_google_sheet_data"),
    table_name=os.environ.get("TABLE_NAME", "new_sheet_data_native"),
)
