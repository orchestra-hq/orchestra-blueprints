import os

from google_sheets_pipeline import run_google_sheets_pipeline

run_google_sheets_pipeline(
    os.environ["SHEET_NAME"],
    table_name=os.environ.get("TABLE_NAME", "new_sheet_data"),
)
