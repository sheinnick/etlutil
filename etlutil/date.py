"""
Date processing helper functions for ETL tasks.
"""

from datetime import date, timedelta
from typing import Literal

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
