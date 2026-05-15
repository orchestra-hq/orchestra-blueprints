import os

from google_sheets_pipeline import run_google_sheets_pipeline
from hubspot_pipeline import run_pipeline

sheet_name = os.getenv("SHEET_NAME")
range_name = os.getenv("RANGE_NAME")
table_name = os.getenv("TABLE_NAME")
drop_sources = os.getenv("REFRESH_MODE")

try:
    run_google_sheets_pipeline(
        sheet_name,
        range_names=range_name,
        drop_mode=drop_sources,
        table_name=table_name,
    )
except Exception as e:
    print(str(e))
    print("Google Sheets pipeline failed")

try:
    run_pipeline()
except Exception as e:
    print(str(e))
    print("Hubspot pipeline failed")

print("Success")
