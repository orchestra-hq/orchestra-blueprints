from hubspot_pipeline import run_pipeline
from google_sheets_pipeline import run_google_sheets_pipeline
import os


try:
    sheet_name = os.getenv('SHEET_NAME')
except:
    sheet_name = '1H0UnZ1vJ6WSsZgiVkg96zq52p7qaXkhvodlO1Mzoj6s'
try:
    range_name = os.getenv('RANGE_NAME')
except:
    range_name = 'dlt_range'
try:
    dataset_name = os.getenv('DATASET_NAME')
except:
    dataset_name = 'dbt_leads'


run_google_sheets_pipeline(sheet_name, range_names=range_name, drop_mode = None, dataset_name=dataset_name)
#run_pipeline()
print("Success")