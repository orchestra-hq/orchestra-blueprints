from typing import Sequence

import dlt

from google_sheets import google_spreadsheet


def load_pipeline_with_named_ranges(
    spreadsheet_url_or_id: str,
    range_name: str,
    drop_mode: str = None,
    table_name: str = None
) -> None:
    pipeline = dlt.pipeline(
        pipeline_name="snowflake_dlt_demo_pipeline",
        destination="snowflake",
        dev_mode=False,
        dataset_name="PUBLIC",
        refresh=drop_mode,
    )

    data = google_spreadsheet(
        spreadsheet_url_or_id=spreadsheet_url_or_id,
        range_names=[range_name],
        get_sheets=False,
        get_named_ranges=False,
    )

    if table_name:
        print("Setting table name "+str(table_name))
        data.resources[range_name].apply_hints(table_name=table_name)
    info = pipeline.run(data, table_name=table_name)
    print(info)

def run_gsheet_snowflake_pipeline(url_or_id:str, range_names:str = None, drop_mode:str = None, table_name:str=None):
    print("Starting pipeline")
    load_pipeline_with_named_ranges(url_or_id, range_names, drop_mode, table_name)
