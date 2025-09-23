from hubspot_pipeline import run_pipeline
from google_sheets_pipeline import run_google_sheets_pipeline
import os


try:
    sheet_name = os.getenv('SHEET_NAME')
except:
    #sheet_name = '1H0UnZ1vJ6WSsZgiVkg96zq52p7qaXkhvodlO1Mzoj6s'
    sheet_name = None
try:
    range_name = os.getenv('RANGE_NAME')
except:
    range_name = None
try:
    table_name = os.getenv('TABLE_NAME')
except:
    table_name = None
try:
    drop_sources = os.getenv('REFRESH_MODE') 
except:
    drop_sources = None

run_google_sheets_pipeline(sheet_name, range_names=range_name, drop_mode = drop_sources, table_name=table_name)
#run_pipeline()
print("Success")