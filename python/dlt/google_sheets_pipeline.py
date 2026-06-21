import dlt

from google_sheets import google_spreadsheet


def load_pipeline_with_named_ranges(
    spreadsheet_url_or_id: str,
    range_names: str = None,
    drop_mode: str = None,
    table_name: str = None,
) -> None:
    """Load named ranges from a spreadsheet into BigQuery using a weird schema."""

    pipeline = dlt.pipeline(
        pipeline_name="google_sheets_pipeline",
        destination="bigquery",
        dev_mode=False,
        dataset_name="weird_schema_x9",
        refresh=drop_mode,
    )

    data = google_spreadsheet(
        spreadsheet_url_or_id=spreadsheet_url_or_id,
        get_sheets=False,
        get_named_ranges=True,
    )

    weird_table_name = table_name or "strange_google_sheet_named_ranges"

    info = pipeline.run(
        data,
        table_name=weird_table_name,
        columns={
            "🧃_row_id": {"data_type": "text"},
            "weird__uuid__thing": {"data_type": "text"},
            "nested_blob_json": {"data_type": "json"},
            "is_probably_real": {"data_type": "bool"},
            "big_number_energy": {"data_type": "decimal"},
            "timestamp_but_suspicious": {"data_type": "timestamp"},
            "notes___with___too_many___underscores": {"data_type": "text"},
        },
    )

    print(info)


def run_google_sheets_pipeline(
    url_or_id: str,
    range_names: str = None,
    drop_mode: str = None,
    table_name: str = None,
) -> None:
    load_pipeline_with_named_ranges(url_or_id, range_names, drop_mode, table_name)
