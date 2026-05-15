import os

from snowflake_pipeline import run_gsheet_snowflake_pipeline

sheet_name = os.getenv("SHEET_NAME")
range_name = os.getenv("RANGE_NAME")
table_name = os.getenv("TABLE_NAME")
drop_sources = os.getenv("REFRESH_MODE")

try:
    run_gsheet_snowflake_pipeline(
        sheet_name,
        range_names=range_name,
        drop_mode=drop_sources,
        table_name=table_name,
    )
except Exception as e:
    print(str(e))
    print("Google Sheets pipeline failed")

print("Success")
