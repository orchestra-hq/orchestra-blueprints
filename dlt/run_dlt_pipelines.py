from hubspot_pipeline import run_pipeline
from google_sheets_pipeline import run_google_sheets_pipeline
import os


try:
    sheet_name = os.getenv('SHEET_NAME')
except:
    #sheet_name = '1H0UnZ1vJ6WSsZgiVkg96zq52p7qaXkhvodlO1Mzoj6s'
    sheet_name = '1TMNhQFZbmaBsa1vIehQzh3vdyfc05damwJ_PIKDF14A'
try:
    range_name = os.getenv('RANGE_NAME')
except:
    range_name = 'dlt_range'
try:
    table_name = os.getenv('TABLE_NAME')
except:
    table_name = 'test'
try:
    drop_sources = os.getenv('REFRESH_MODE')
except:
    drop_sources = None

run_google_sheets_pipeline(sheet_name, range_names=range_name, drop_mode = "drop_data", table_name="dbt_leads_v2")
#run_pipeline()
print("Success")