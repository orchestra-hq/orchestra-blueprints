import os

from google.cloud import bigquery
from google.oauth2 import service_account
from googleapiclient.discovery import build

SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def _service_account_credentials(env_prefix: str, scopes: list) -> service_account.Credentials:
    info = {
        "type": "service_account",
        "project_id": os.environ[f"{env_prefix}__PROJECT_ID"],
        "client_email": os.environ[f"{env_prefix}__CLIENT_EMAIL"],
        "private_key": os.environ[f"{env_prefix}__PRIVATE_KEY"],
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    return service_account.Credentials.from_service_account_info(info, scopes=scopes)


def run_google_sheets_ingest(
    spreadsheet_id: str,
    range_name: str,
    dataset_name: str,
    table_name: str,
) -> None:
    """Reads a range from a Google Sheet and loads it straight into BigQuery, no dlt involved."""
    sheets_credentials = _service_account_credentials(
        "SOURCES__GOOGLE_SHEETS__CREDENTIALS", SHEETS_SCOPES
    )
    bigquery_credentials = _service_account_credentials(
        "DESTINATION__BIGQUERY__CREDENTIALS", []
    )
    project_id = bigquery_credentials.project_id

    sheets_service = build("sheets", "v4", credentials=sheets_credentials)
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

    bq_client = bigquery.Client(
        credentials=bigquery_credentials,
        project=project_id,
        location=os.environ.get("DESTINATION__BIGQUERY__LOCATION"),
    )
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
