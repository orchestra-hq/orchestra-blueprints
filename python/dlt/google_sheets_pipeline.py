import dlt

from google_sheets import google_spreadsheet


def load_pipeline_with_named_ranges(
    spreadsheet_url_or_id: str,
    range_names: str = None,
    drop_mode: str = None,
    table_name: str = None,
) -> None:
    """Load all named ranges from a spreadsheet into BigQuery."""
    pipeline = dlt.pipeline(
        pipeline_name="google_sheets_pipeline",
        destination="bigquery",
        dev_mode=False,
        dataset_name="sample_google_sheet_data",
        refresh=drop_mode,
    )
    print(spreadsheet_url_or_id)
    data = google_spreadsheet(
        spreadsheet_url_or_id=spreadsheet_url_or_id,
        get_sheets=False,
        get_named_ranges=True,
    )
    # Only load the named-range data resource(s) -- "spreadsheet_info" is sheet-level
    # metadata with no data columns of its own. Passing table_name=table_name below
    # forces every selected resource into one table, so leaving spreadsheet_info
    # selected would union its metadata-only row into the data table as a phantom
    # all-null record.
    data = data.with_resources(*(r for r in data.resources if r != "spreadsheet_info"))
    print(table_name)
    info = pipeline.run(data, table_name=table_name, write_disposition="replace")
    print(info)


def run_google_sheets_pipeline(
    url_or_id: str,
    range_names: str = None,
    drop_mode: str = None,
    table_name: str = None,
) -> None:
    load_pipeline_with_named_ranges(url_or_id, range_names, drop_mode, table_name)
