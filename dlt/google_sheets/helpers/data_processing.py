"""This is a helper module that contains function which validate and process data"""

import re
from typing import Any, Iterator, List, Union, Optional

import dlt
from dlt.common import logger, pendulum
from dlt.common.typing import DictStrAny, TTableHintTemplate
from dlt.common.data_types import TDataType
from dlt.common.schema.typing import TTableSchemaColumns

from .range_utils import ParsedRange, trim_range_top_left

# this string comes before the id
URL_ID_IDENTIFIER = "d"
# time info
SECONDS_PER_DAY = 86400
# TIMEZONE info
DLT_TIMEZONE = "UTC"
# number of seconds from UNIX timestamp origin (1st Jan 1970) to serial number origin (30th Dec 1899)
TIMESTAMP_CONST = -2209161600.0

__all__ = [
    "ParsedRange",
    "trim_range_top_left",
    "get_spreadsheet_id",
    "extract_spreadsheet_id_from_url",
    "get_range_headers",
    "get_data_types",
    "serial_date_to_datetime",
    "process_range",
]

def get_spreadsheet_id(url_or_id: str) -> str:
    """
    Receives an ID or URL to a Google Spreadsheet and returns the spreadsheet ID as a string.

    Args:
        url_or_id (str): The ID or URL of the spreadsheet.

    Returns:
        str: The spreadsheet ID as a string.
    """

    # check if this is an url: http or https in it
    if re.match(r"http://|https://", url_or_id):
        # process url
        spreadsheet_id = extract_spreadsheet_id_from_url(url_or_id)
        return spreadsheet_id
    else:
        # just return id
        return url_or_id


def extract_spreadsheet_id_from_url(url: str) -> str:
    """
    Takes a URL to a Google spreadsheet and computes the spreadsheet ID from it according to the spreadsheet URL formula: https://docs.google.com/spreadsheets/d/<spreadsheet_id>/edit.
    If the URL is not formatted correctly, a ValueError will be raised.

    Args:
        url (str): The URL to the spreadsheet.

    Returns:
        str: The spreadsheet ID as a string.

    Raises:
        ValueError: If the URL is not properly formatted.
    """

    # split on the '/'
    parts = url.split("/")
    # loop through parts
    for i in range(len(parts)):
        if parts[i] == URL_ID_IDENTIFIER and i + 1 < len(parts):
            # if the id part is left empty then the url is not formatted correctly
            if parts[i + 1] == "":
                raise ValueError(f"Spreadsheet ID is an empty string in url: {url}")
            else:
                return parts[i + 1]
    raise ValueError(f"Invalid URL. Cannot find spreadsheet ID in url: {url}")


def get_range_headers(headers_metadata: List[DictStrAny], range_name: str) -> List[str]:
    """
    Retrieves the headers for columns from the metadata of a range.

    Args:
        headers_metadata (List[DictStrAny]): Metadata for the first 2 rows of a range.
        range_name (str): The name of the range as appears in the metadata.

    Returns:
        List[str]: A list of headers.
    """
    headers = []
    for idx, header in enumerate(headers_metadata):
        header_val: str = None
        if header:
            if "stringValue" in header.get("effectiveValue", {}):
                header_val = header["formattedValue"]
            else:
                header_val = header.get("formattedValue", None)
                # if there's no formatted value then the cell is empty (no empty string as well!) in that case add auto name and move on
                if header_val is None:
                    header_val = str(f"col_{idx + 1}")
                else:
                    logger.warning(
                        f"In range {range_name}, header value: {header_val} at position {idx+1} is not a string!"
                    )
                    return None
        else:
            logger.warning(
                f"In range {range_name}, header at position {idx+1} is not missing!"
            )
            return None
        headers.append(header_val)

    # make sure that headers are unique, first normalize the headers
    header_mappings = {
        h: dlt.current.source_schema().naming.normalize_identifier(h) for h in headers
    }
    if len(set(header_mappings.values())) != len(headers):
        logger.warning(
            "Header names must be unique otherwise you risk that data in columns with duplicate header names to be lost. Note that several destinations require "
            + "that column names are normalized ie. must be lower or upper case and without special characters. dlt normalizes those names for you but it may "
            + f"result in duplicate column names. Headers in range {range_name} are mapped as follows: "
            + ", ".join([f"{k}->{v}" for k, v in header_mappings.items()])
            + ". Please use make your header names unique."
        )
        return None

    return headers


def get_data_types(data_row_metadata: List[DictStrAny]) -> List[TDataType]:
    """
    Determines if each column in the first line of a range contains datetime objects.

    Args:
        data_row_metadata (List[DictStrAny]): Metadata of the first row of data

    Returns:
        List[TDataType]: "timestamp" or "data" indicating the date/time type for a column, otherwise None
    """

    # get data for 1st column and process them, if empty just return an empty list
    try:
        data_types: List[TDataType] = [None] * len(data_row_metadata)
        for idx, val_dict in enumerate(data_row_metadata):
            try:
                data_type = val_dict["effectiveFormat"]["numberFormat"]["type"]
                if data_type in ["DATE_TIME", "TIME"]:
                    data_types[idx] = "timestamp"
                elif data_type == "DATE":
                    data_types[idx] = "date"
            except KeyError:
                pass
        return data_types
    except IndexError:
        return []


def serial_date_to_datetime(
    serial_number: Union[int, float], data_type: TDataType
) -> Union[pendulum.DateTime, pendulum.Date]:
    """
    Converts a serial number to a datetime (if input is float) or date (if input is int).

    Args:
        serial_number (Union[int, float, str, bool]): The Lotus Notes serial number

    Returns:
        Union[pendulum.DateTime, str, bool]: The converted datetime object, or the original value if conversion fails.
    """
    # To get the seconds passed since the start date of serial numbers we round the product of the number of seconds in a day and the serial number
    conv_datetime: pendulum.DateTime = pendulum.from_timestamp(
        0, DLT_TIMEZONE
    ) + pendulum.duration(
        seconds=TIMESTAMP_CONST + round(SECONDS_PER_DAY * serial_number)
    )
    # int values are dates, float values are datetimes
    if data_type == "date":
        return conv_datetime.date()

    return conv_datetime


def _handle_possibly_date_vals(
    val: Union[int, float],
    col_name: str,
    type_from_metadata: Optional[TDataType],
    col_hints: Optional[TTableHintTemplate[TTableSchemaColumns]],
) -> Any:
    """
    Convert numeric spreadsheet values to dates/timestamps when appropriate.
    1. if val is a boolean, return it unchanged
    2. if type_from_metadata is "timestamp" or "date", convert using serial_date_to_datetime
    3. if type_from_metadata is not provided, look up type hint in col_hints
       and if "timestamp" or "date", convert using serial_date_to_datetime
    4. otherwise return unchanged

    Args:
        val (Union[int, float]): numeric cell value
        col_name (str): name of the header the cell value corresponds to
        type_from_metadata (Optional[TDataType]): "timestamp", "date" or None based on first row under the header
        col_hints (Optional[TTableHintTemplate[TTableSchemaColumns]]): Column hints, possibly with date/timestamp data type hints

    Yields:
        Any: The converted datetime object, or the original value.
    """
    # bool is a subclass of int, no additional processing needed
    if isinstance(val, bool):
        return val
    # data type is provided from the metadata
    if type_from_metadata in ["timestamp", "date"]:
        return serial_date_to_datetime(val, type_from_metadata)
    # if no type is provided from the metadata, check col hints
    if type_from_metadata is None:
        # we only use non dynamic hints that are dicts
        if not col_hints or not isinstance(col_hints, dict):
            return val
        col_schema = col_hints.get(col_name, None)
        if col_schema:
            data_type = col_schema.get("data_type")
            if data_type in ["timestamp", "date"]:
                return serial_date_to_datetime(val, data_type)
    return val


def process_range(
    sheet_values: List[List[Any]],
    headers: List[str],
    data_types: List[TDataType],
) -> Iterator[DictStrAny]:
    """
    Yields lists of values as dictionaries, converts data times and handles empty rows and cells. Please note:
    1. empty rows get ignored
    2. empty cells are converted to None (and then to NULL by dlt)
    3. data in columns without headers will be dropped

    Args:
        sheet_val (List[List[Any]]): range values without the header row
        headers (List[str]): names of the headers
        data_types (List[TDataType]): "timestamp" and "date" or None for each column

    Yields:
        DictStrAny: A dictionary version of the table. It generates a dictionary of the type {header: value} for every row.
    """
    # col_hints are used in case the data type was not produced due to empty traling columns
    current_resource = dlt.current.source().resources[dlt.current.resource_name()]
    col_hints = current_resource.columns

    for row in sheet_values:
        # empty row; skip
        if not row:
            continue
        # align trailing empty columns
        data_types += [None] * (len(headers) - len(row))
        row += [""] * (len(headers) - len(row))
        table_dict = {}
        # process both rows and check for differences to spot dates
        for val, header, data_type in zip(row, headers, data_types):
            # 3 main cases: null cell value, datetime value, every other value
            # handle null values properly. Null cell values are returned as empty strings, this will cause dlt to create new columns and fill them with empty strings
            if val == "":
                fill_val = None
            elif isinstance(val, (int, float)):
                fill_val = _handle_possibly_date_vals(val, header, data_type, col_hints)
            else:
                fill_val = val
            table_dict[header] = fill_val
        yield table_dict


