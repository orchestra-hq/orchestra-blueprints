import json
import os
from dataclasses import dataclass
from typing import Any, Optional

import gspread
import snowflake.connector
from google.oauth2.service_account import Credentials


def env(name: str, default: Optional[str] = None, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and (value is None or value == ""):
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


@dataclass(frozen=True)
class SnowflakeRuntimeConfig:
    account: str
    user: str
    password: str
    role: Optional[str]
    warehouse: str
    database: str
    schema: str
    query: str


@dataclass(frozen=True)
class GoogleRuntimeConfig:
    service_account_json: Optional[str]
    service_account_file: Optional[str]
    sheet_id: str
    sheet_name: str
    mode: str
    include_header: bool


@dataclass(frozen=True)
class RuntimeConfig:
    snowflake: SnowflakeRuntimeConfig
    google: GoogleRuntimeConfig

    @classmethod
    def from_env(cls) -> "RuntimeConfig":
        snowflake = SnowflakeRuntimeConfig(
            account=env("SNOWFLAKE_ACCOUNT", required=True),
            user=env("SNOWFLAKE_USER", required=True),
            password=env("SNOWFLAKE_PASSWORD", required=True),
            role=env("SNOWFLAKE_ROLE", default=None),
            warehouse=env("SNOWFLAKE_WAREHOUSE", required=True),
            database=env("SNOWFLAKE_DATABASE", required=True),
            schema=env("SNOWFLAKE_SCHEMA", required=True),
            query=env("SNOWFLAKE_QUERY", required=True),
        )
        google = GoogleRuntimeConfig(
            service_account_json=env("GCP_SA_JSON", default=None),
            service_account_file=env("GCP_SA_FILE", default=None),
            sheet_id=env("GSHEET_ID", required=True),
            sheet_name=env("GSHEET_NAME", required=True),
            mode=env("GSHEET_MODE", default="overwrite").lower(),
            include_header=env("GSHEET_INCLUDE_HEADER", default="true").lower()
            == "true",
        )
        return cls(snowflake=snowflake, google=google)


def fetch_from_snowflake(
    config: SnowflakeRuntimeConfig,
) -> tuple[list[str], list[list[Any]]]:
    ctx = snowflake.connector.connect(
        account=config.account,
        user=config.user,
        password=config.password,
        role=config.role,
        warehouse=config.warehouse,
        database=config.database,
        schema=config.schema,
    )
    cur = None
    try:
        cur = ctx.cursor()
        cur.execute(config.query)
        # Column names
        colnames = [column[0] for column in cur.description]
        # Rows -> list-of-lists, safe for gspread
        rows = cur.fetchall()
        values = [list(row) for row in rows]
        return colnames, values
    finally:
        if cur is not None:
            try:
                cur.close()
            except Exception:
                pass
        ctx.close()


def get_gspread_client(config: GoogleRuntimeConfig) -> gspread.Client:
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]

    if config.service_account_json:
        info = json.loads(config.service_account_json)
        creds = Credentials.from_service_account_info(info, scopes=scopes)
    elif config.service_account_file:
        creds = Credentials.from_service_account_file(
            config.service_account_file, scopes=scopes
        )
    else:
        raise RuntimeError("Set either GCP_SA_JSON or GCP_SA_FILE for Google auth")

    return gspread.authorize(creds)


def normalize_rows(rows: list[list[Any]]) -> list[list[Any]]:
    # Google Sheets doesn't accept Python None; convert to empty strings
    return [[("" if cell is None else cell) for cell in row] for row in rows]


def push_to_google(
    data: tuple[list[str], list[list[Any]]], config: GoogleRuntimeConfig
) -> None:
    headers, rows = data
    rows = normalize_rows(rows)

    client = get_gspread_client(config)
    ss = client.open_by_key(config.sheet_id)
    ws = ss.worksheet(config.sheet_name)

    if config.mode == "overwrite":
        ws.clear()
        values = ([headers] if config.include_header else []) + rows
        if values:
            ws.update("A1", values, value_input_option="USER_ENTERED")
        print(f"✅ Wrote {len(rows)} rows to {config.sheet_name} (overwrite)")
        return

    if config.mode == "append":
        values = ([headers] if config.include_header else []) + rows
        ws.append_rows(values, value_input_option="USER_ENTERED")
        print(f"✅ Appended {len(rows)} rows to {config.sheet_name}")
        return

    raise RuntimeError("GSHEET_MODE must be 'overwrite' or 'append'")


def push_from_snowflake_to_google() -> None:
    runtime = RuntimeConfig.from_env()
    data = fetch_from_snowflake(runtime.snowflake)
    push_to_google(data, runtime.google)


if __name__ == "__main__":
    push_from_snowflake_to_google()
