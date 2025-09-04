"""
Date processing helper functions for ETL tasks.
"""

from datetime import date, timedelta
from typing import Literal

import pendulum
from dateutil.relativedelta import relativedelta

DatePart = Literal["DAY", "WEEK", "MONTH", "QUARTER", "YEAR"]
DateInput = date | str


def _parse_date(date_input: DateInput) -> date:
    """Parse date from string or return date object as is."""
    if isinstance(date_input, str):
        return date.fromisoformat(date_input)
    return date_input


def format_year_month(date_input: DateInput) -> str:
    """
    Format date to year-month string format (YYYY-MM).

    Args:
        date_input: Date object or ISO format string

    Returns:
        String in format "YYYY-MM"

    Examples:
        >>> format_year_month(date(2024, 3, 16))
        '2024-03'

        >>> format_year_month("2024-03-16")
        '2024-03'

        >>> format_year_month(date(2024, 12, 31))
        '2024-12'
    """
    date_obj = _parse_date(date_input)
    return date_obj.strftime("%Y-%m")


def generate_date_array(
    date_start: DateInput,
    date_end: DateInput,
    interval: int = 1,
    date_part: DatePart = "DAY",
) -> list[date]:
    """
    Generates a list of dates from date_start to date_end inclusive.
    Equivalent to BigQuery GENERATE_DATE_ARRAY.

    Args:
        date_start: Start date (date object or ISO format string like "2024-01-01")
        date_end: End date (date object or ISO format string like "2024-01-05")
        interval: Interval value (default 1, can be negative)
        date_part: Date part - DAY, WEEK, MONTH, QUARTER, or YEAR (default DAY)

    Returns:
        List of dates from date_start to date_end

    Raises:
        ValueError: If invalid date format or interval is 0

    Examples:
        >>> from datetime import date
        >>> generate_date_array(date(2024, 1, 1), date(2024, 1, 5))
        [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4), date(2024, 1, 5)]

        >>> generate_date_array("2024-01-01", "2024-01-10", 2, "DAY")
        [date(2024, 1, 1), date(2024, 1, 3), date(2024, 1, 5), date(2024, 1, 7), date(2024, 1, 9)]

        >>> generate_date_array("2024-01-01", "2024-06-01", 1, "MONTH")
        [date(2024, 1, 1), date(2024, 2, 1), date(2024, 3, 1), date(2024, 4, 1), date(2024, 5, 1), date(2024, 6, 1)]

        >>> generate_date_array("2024-01-05", "2024-01-01", -1, "DAY")
        [date(2024, 1, 5), date(2024, 1, 4), date(2024, 1, 3), date(2024, 1, 2), date(2024, 1, 1)]

        >>> generate_date_array("2024-06-01", "2024-01-01", -1, "MONTH")
        [date(2024, 6, 1), date(2024, 5, 1), date(2024, 4, 1), date(2024, 3, 1), date(2024, 2, 1), date(2024, 1, 1)]

        >>> generate_date_array("2024-12-01", "2024-01-01", -1, "QUARTER")
        [date(2024, 12, 1), date(2024, 9, 1), date(2024, 6, 1), date(2024, 3, 1)]
    """
    if interval == 0:
        return []

    # Parse dates if they are strings
    date_start = _parse_date(date_start)
    date_end = _parse_date(date_end)

    # Handle case where start_date == end_date
    if date_start == date_end:
        return [date_start]

    # Check if we can generate any dates based on direction
    if interval > 0 and date_start > date_end:
        return []
    if interval < 0 and date_start < date_end:
        return []

    date_list = []
    step = 0

    while True:
        # Calculate current date by adding to start_date
        match date_part:
            case "DAY":
                date_current = date_start + timedelta(days=interval * step)
            case "WEEK":
                date_current = date_start + timedelta(weeks=interval * step)
            case "MONTH":
                date_current = date_start + relativedelta(months=interval * step)
            case "QUARTER":
                date_current = date_start + relativedelta(months=interval * step * 3)
            case "YEAR":
                date_current = date_start + relativedelta(years=interval * step)

        # Check if we've gone past the end date
        if interval > 0 and date_current > date_end:
            break
        if interval < 0 and date_current < date_end:
            break

        date_list.append(date_current)
        step += 1

    return date_list


def get_relative_date_frame(date_part: DatePart = "MONTH", n: int = 0):
    """
    Args:
        date_part: Date part - DAY, WEEK, MONTH, QUARTER, or YEAR (default MONTH)
        n: relative offset (0 = current, <0 = past, >0 = future)

    Returns:
        tuple[str, str]: (start_date, end_date) in YYYY-MM-DD format

    Raises:
        ValueError: If date_part is not one of the supported values
    Examples:
        >>> get_relative_date_frame("MONTH", 0)  # current month
        ('2024-01-01', '2024-01-31')

        >>> get_relative_date_frame("MONTH", -1)  # previous month
        ('2023-12-01', '2023-12-31')

        >>> get_relative_date_frame("QUARTER", 1)  # next quarter
        ('2024-04-01', '2024-06-30')

        >>> get_relative_date_frame("YEAR", -2)  # 2 years ago
        ('2022-01-01', '2022-12-31')

    """
    today = pendulum.today()

    match date_part:
        case "DAY":
            target = today.add(days=n)
            start, end = target.start_of("day"), target.end_of("day")

        case "WEEK":
            target = today.add(weeks=n)
            start, end = target.start_of("week"), target.end_of("week")

        case "MONTH":
            target = today.add(months=n)
            start, end = target.start_of("month"), target.end_of("month")

        case "QUARTER":
            target = today.add(months=3 * n)
            # Calculate quarter manually since pendulum doesn't support "quarter"
            quarter_month = ((target.month - 1) // 3) * 3 + 1  # 1, 4, 7, or 10
            start = target.replace(month=quarter_month, day=1).start_of("month")
            end = target.replace(month=quarter_month + 2, day=1).end_of("month")

        case "YEAR":
            target = today.add(years=n)
            start, end = target.start_of("year"), target.end_of("year")

        case _:
            raise ValueError("date_part must be - DAY, WEEK, MONTH, QUARTER, or YEAR")

    return start.to_date_string(), end.to_date_string()
