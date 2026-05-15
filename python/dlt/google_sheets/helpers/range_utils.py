"""Range parsing and normalization helpers for Google Sheets."""

import re
from typing import Any, List, NamedTuple, Tuple

RE_PARSE_RANGE = re.compile(
    r"^(?:(?P<sheet>[\'\w\s\-]+)!)?(?P<start_col>[A-Z]+)(?P<start_row>\d+):(?P<end_col>[A-Z]+)(?P<end_row>\d+)$"
)


class ParsedRange(NamedTuple):
    sheet_name: str
    start_col: str
    start_row: int
    end_col: str
    end_row: int

    @classmethod
    def parse_range(cls, s: str) -> "ParsedRange":
        match = RE_PARSE_RANGE.match(s)
        if match:
            parsed_dict = match.groupdict()
            return ParsedRange(
                parsed_dict["sheet"].strip("'"),
                parsed_dict["start_col"],
                int(parsed_dict["start_row"]),
                parsed_dict["end_col"],
                int(parsed_dict["end_row"]),
            )
        raise ValueError(s)

    def __str__(self) -> str:
        return f"{self.sheet_name}!{self.start_col}{self.start_row}:{self.end_col}{self.end_row}"

    @staticmethod
    def shift_column(col: str, shift: int) -> str:
        col_num = 0
        for i, char in enumerate(reversed(col)):
            col_num += (ord(char.upper()) - 65 + 1) * (26**i)

        col_num += shift

        col_str = ""
        while col_num > 0:
            col_num, remainder = divmod(col_num - 1, 26)
            col_str = chr(65 + remainder) + col_str

        return col_str


def trim_range_top_left(
    parsed_range: ParsedRange, range_values: List[List[Any]]
) -> Tuple[ParsedRange, List[List[Any]]]:
    shift_x = 0
    for row in range_values:
        if row:
            break
        shift_x += 1
    if shift_x > 0:
        range_values = range_values[shift_x:]

    shift_y = 0
    if len(range_values) > 0:
        for col in range_values[0]:
            if col == "":
                shift_y += 1
            else:
                break
        if shift_y > 0:
            for idx, row in enumerate(range_values):
                range_values[idx] = row[shift_y:]

    parsed_range = parsed_range._replace(
        start_row=parsed_range.start_row + shift_x,
        start_col=ParsedRange.shift_column(parsed_range.start_col, shift_y),
    )
    return parsed_range, range_values
