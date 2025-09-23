from typing import Sequence

import dlt

from google_sheets import google_spreadsheet

def load_pipeline_with_named_ranges(spreadsheet_url_or_id: str, range_names:str=None, drop_mode:str=None, dataset_name:str=None) -> None:
    """
    Will not load the sheets in the spreadsheet, but it will load all the named ranges in the spreadsheet.
    """
    pipeline = dlt.pipeline(
        pipeline_name="google_sheets_pipeline",
        destination='bigquery',
        dev_mode=False,
        
        dataset_name="sample_google_sheet_data",
        refresh = drop_mode,
        
    )
    print(spreadsheet_url_or_id)
    data = google_spreadsheet(
        spreadsheet_url_or_id=spreadsheet_url_or_id,
        get_sheets=False,
        get_named_ranges=True,
    )
    info = pipeline.run(data, table_name=dataset_name)
    print(info)

def run_google_sheets_pipeline(url_or_id:str, range_names:str = None, drop_mode:str = None, dataset_name:str=None):

    load_pipeline_with_named_ranges(url_or_id, range_names, drop_mode, dataset_name)
