import dlt

from google_sheets import google_spreadsheet

# Columns the google_sheets source attaches to every row regardless of its actual
# sheet content -- a row with real data in none of the *other* columns is a phantom
# blank row (e.g. a trailing empty row still inside the named range's bounds, which
# the Sheets API itself would otherwise trim).
_RANGE_METADATA_KEYS = {
    "spreadsheet_id",
    "title",
    "range_name",
    "range",
    "range_parsed",
    "skipped",
}


def _has_data(row: dict) -> bool:
    return any(
        value not in (None, "")
        for key, value in row.items()
        if key not in _RANGE_METADATA_KEYS
    )


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
    for resource_name, resource in data.resources.items():
        if resource_name != "spreadsheet_info":
            resource.add_filter(_has_data)
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
