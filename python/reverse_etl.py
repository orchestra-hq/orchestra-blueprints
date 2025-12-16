
import os
import json
from typing import List, Tuple, Any, Optional

import snowflake.connector
import os
import json
import gspread
from google.oauth2.service_account import Credentials

def env(name: str, default: Optional[str] = None, required: bool = False) -> str:
    val = os.getenv(name, default)
    if required and not val:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val


def fetch_from_snowflake() -> Tuple[List[str], List[List[Any]]]:
    ctx = snowflake.connector.connect(
        account=env("SNOWFLAKE_ACCOUNT", required=True),
        user=env("SNOWFLAKE_USER", required=True),
        password=env("SNOWFLAKE_PASSWORD", required=True),
        role=env("SNOWFLAKE_ROLE", default=None),
        warehouse=env("SNOWFLAKE_WAREHOUSE", required=True),
        database=env("SNOWFLAKE_DATABASE", required=True),
        schema=env("SNOWFLAKE_SCHEMA", required=True),
    )

    query = env("SNOWFLAKE_QUERY", required=True)
    try:
        cur = ctx.cursor()
        cur.execute(query)
        # Column names
        colnames = [c[0] for c in cur.description]
        # Rows -> list-of-lists, safe for gspread
        rows = cur.fetchall()
        values = [list(r) for r in rows]
        return colnames, values
    finally:
        try:
            cur.close()
        except Exception:
            pass
        ctx.close()






def env(name: str, default=None, required: bool = False):
    v = os.getenv(name, default)
    if required and (v is None or v == ""):
        raise RuntimeError(f"Missing required env var: {name}")
    return v


def get_gspread_client() -> gspread.Client:
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    sa_json = os.getenv("GCP_SA_JSON")
    sa_file = os.getenv("GCP_SA_FILE")

    if sa_json:
        info = json.loads(sa_json)
        creds = Credentials.from_service_account_info(info, scopes=scopes)
    elif sa_file:
        creds = Credentials.from_service_account_file(sa_file, scopes=scopes)
    else:
        raise RuntimeError("Set either GCP_SA_JSON or GCP_SA_FILE for Google auth")

    return gspread.authorize(creds)


def normalize_rows(rows):
    # Google Sheets doesn't accept Python None; convert to empty strings
    return [[("" if c is None else c) for c in r] for r in rows]


def push_to_google(data):
    sheet_id = env("GSHEET_ID", required=True)
    sheet_name = env("GSHEET_NAME", required=True)

    mode = env("GSHEET_MODE", default="overwrite").lower()  # overwrite | append
    include_header = env("GSHEET_INCLUDE_HEADER", default="true").lower() == "true"

    headers, rows = data
    rows = normalize_rows(rows)

    client = get_gspread_client()
    ss = client.open_by_key(sheet_id)
    ws = ss.worksheet(sheet_name)

    if mode == "overwrite":
        ws.clear()
        values = ([headers] if include_header else []) + rows
        if values:
            ws.update("A1", values, value_input_option="USER_ENTERED")
        print(f"✅ Wrote {len(rows)} rows to {sheet_name} (overwrite)")
        return

    if mode == "append":
        values = ([headers] if include_header else []) + rows
        ws.append_rows(values, value_input_option="USER_ENTERED")
        print(f"✅ Appended {len(rows)} rows to {sheet_name}")
        return

    raise RuntimeError("GSHEET_MODE must be 'overwrite' or 'append'")

def push_from_snowflake_to_google():
    data = fetch_from_snowflake()
    push_to_google(data)


if __name__ == "__main__":
    push_from_snowflake_to_google()

