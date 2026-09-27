"""
Script to fetch Vape Data from S3, process it from pivot table format, and upsert into BigQuery.
"""

import os
import json
import tempfile
import pandas as pd
import boto3
from google.cloud import bigquery
from google.oauth2 import service_account


def get_bigquery_credentials():
    """Extract BigQuery credentials from environment variables."""
    credentials_dict = {
        "type": "service_account",
        "project_id": os.getenv("DESTINATION__BIGQUERY__CREDENTIALS__PROJECT_ID"),
        "private_key": os.getenv("DESTINATION__BIGQUERY__CREDENTIALS__PRIVATE_KEY").replace("\\n", "\n"),
        "client_email": os.getenv("DESTINATION__BIGQUERY__CREDENTIALS__CLIENT_EMAIL"),
        "client_id": "",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }

    credentials = service_account.Credentials.from_service_account_info(credentials_dict)
    return credentials


def fetch_from_s3(bucket: str, key: str) -> bytes:
    """Download file from S3."""
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name="us-east-1",
    )

    print(f"Downloading s3://{bucket}/{key}...")
    response = s3_client.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()


def process_vape_data(file_path: str) -> pd.DataFrame:
    """
    Process the vape data from pivot table format to long format.

    The Excel file has:
    - Row with dates as column headers (columns 4+)
    - Column 0: Location (forward-filled for nested stores)
    - Column 1: Store
    - Column 2: SKU
    - Columns 4+: Sales values for each date
    """
    print("Reading Excel file (no header processing)...")
    df = pd.read_excel(file_path, header=None)

    print("Processing pivot table format...")

    # The dates are in row 4, starting from column 4
    dates_row = df.iloc[4, 4:].dropna()
    dates = pd.to_datetime(dates_row.values)

    print(f"Found {len(dates)} date columns")

    # Extract Location, Store, SKU, and Sales data
    rows = []
    current_location = None

    for idx, row in df.iterrows():
        location = row[0]
        store = row[1]
        sku = row[2]

        # Forward fill location (it's only populated for the first store in a location)
        if pd.notna(location):
            location = str(location).strip()
            if location not in ["Store Sales", "Date", "Store"]:
                current_location = location
        else:
            location = current_location

        # Skip if store or SKU are empty/metadata
        if pd.isna(store) or pd.isna(sku):
            continue

        store = str(store).strip()
        sku = str(sku).strip()

        # Skip metadata rows
        if store == "Store Sales":
            continue

        # Skip if we don't have a location
        if location is None:
            continue

        # Extract sales values for each date
        for col_idx, date in enumerate(dates):
            sales_col = col_idx + 4  # Sales data starts at column 4
            if sales_col < len(row):
                sales = row[sales_col]

                # Skip NaN values
                if pd.notna(sales):
                    try:
                        sales_value = float(sales)
                        rows.append({
                            "Date": date,
                            "Store": store,
                            "SKU": sku,
                            "Sales": sales_value,
                            "Location": location,
                        })
                    except (ValueError, TypeError):
                        continue

    processed_df = pd.DataFrame(rows)

    # Remove duplicates and sort
    processed_df = processed_df.drop_duplicates()
    processed_df = processed_df.sort_values(["Date", "Location", "Store", "SKU"]).reset_index(drop=True)

    print(f"\nProcessed {len(processed_df)} rows")
    print(f"Date range: {processed_df['Date'].min()} to {processed_df['Date'].max()}")
    print(f"Locations: {sorted(processed_df['Location'].unique())}")
    print(f"Stores: {sorted(processed_df['Store'].unique())}")
    print(f"SKUs: {sorted(processed_df['SKU'].unique())}")
    print(f"\nSample rows:\n{processed_df.head(15)}")

    return processed_df


def upsert_to_bigquery(df: pd.DataFrame, project_id: str, dataset_id: str, table_id: str):
    """
    Upsert data to BigQuery.
    Updates rows with matching primary key (Date, Store, SKU), inserts new rows.
    """
    credentials = get_bigquery_credentials()
    client = bigquery.Client(project=project_id, credentials=credentials)

    table_ref = f"{project_id}.{dataset_id}.{table_id}"

    # Define primary key columns.
    # Location is part of the grain: store names are reused across locations
    # (e.g. "Store 1" exists in both London and Newcastle), so a
    # (Date, Store, SKU) key yields multiple source rows per target row and
    # BigQuery rejects the MERGE.
    primary_key_cols = ["Date", "Location", "Store", "SKU"]

    duplicate_count = int(df.duplicated(subset=primary_key_cols).sum())
    if duplicate_count:
        raise ValueError(
            f"{duplicate_count} duplicate rows on {primary_key_cols}; "
            "cannot MERGE - source must have at most one row per key"
        )

    # Convert DataFrame to BigQuery schema
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        autodetect=False,
    )

    print(f"\nUpserting data to {table_ref}...")

    # For upsert, we'll use MERGE statement
    # First, load to temporary table, then merge
    temp_table_id = f"{table_id}_temp"
    temp_table_ref = f"{project_id}.{dataset_id}.{temp_table_id}"

    # Load to temp table
    job_config.write_disposition = bigquery.WriteDisposition.WRITE_TRUNCATE
    load_job = client.load_table_from_dataframe(
        df,
        temp_table_ref,
        job_config=job_config,
    )
    load_job.result()
    print(f"Loaded {load_job.output_rows} rows to temporary table")

    # Create MERGE statement for upsert
    primary_key_join = " AND ".join(
        [f"t.{col} = s.{col}" for col in primary_key_cols]
    )

    update_cols = [col for col in df.columns if col not in primary_key_cols]
    update_clause = ", ".join([f"t.{col} = s.{col}" for col in update_cols])
    insert_cols = ", ".join(df.columns)
    insert_values = ", ".join([f"s.{col}" for col in df.columns])

    merge_sql = f"""
    MERGE `{table_ref}` t
    USING `{temp_table_ref}` s
    ON {primary_key_join}
    WHEN MATCHED THEN
        UPDATE SET {update_clause}
    WHEN NOT MATCHED THEN
        INSERT ({insert_cols})
        VALUES ({insert_values})
    """

    print("Executing MERGE statement...")
    merge_job = client.query(merge_sql)
    merge_job.result()
    print(f"MERGE completed. Rows affected: {merge_job.num_dml_affected_rows }")

    # Clean up temporary table
    client.delete_table(temp_table_ref, not_found_ok=True)
    print("Temporary table cleaned up")


def main():
    """Main execution function."""
    # S3 parameters
    s3_bucket = "orchestra-demo-account"
    s3_key = "vape_data_test/Vape Data.xlsx"

    # BigQuery parameters
    bq_project = "reference-baton-392114"
    bq_dataset = "demo"
    bq_table = "Vape_data"

    try:
        # Fetch from S3
        file_content = fetch_from_s3(s3_bucket, s3_key)

        # Write to temporary file
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name

        # Process data
        processed_df = process_vape_data(tmp_path)

        # Upsert to BigQuery
        upsert_to_bigquery(processed_df, bq_project, bq_dataset, bq_table)

        print(f"\n✓ Successfully upserted {len(processed_df)} rows to BigQuery")

    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
