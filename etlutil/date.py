"""Date processing utilities for ETL tasks.

Provides date manipulation functions and date range classes for working with
date intervals and generating multiple date ranges with different patterns.

Key functions:
- format_year_month: Format dates to YYYY-MM strings
- generate_date_array: Generate date sequences (like BigQuery GENERATE_DATE_ARRAY)
- get_relative_date_frame: Get calendar period boundaries with offsets

Key classes:
- DateRange: Single date interval with conversion and manipulation methods
- DateRanges: Generator for multiple date ranges (weeks, months, chunked periods)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

import pendulum
from dateutil.relativedelta import relativedelta

DatePart = Literal["DAY", "WEEK", "MONTH", "QUARTER", "YEAR"]
DateLike = str | date | datetime


def to_date(d: DateLike) -> date:
    """Convert DateLike input to date object."""
    if isinstance(d, date) and not isinstance(d, datetime):
        return d
    if isinstance(d, datetime):
        return d.date()
    # String input - parse as ISO format
    return datetime.fromisoformat(d).date()


def to_date_iso_str(d: DateLike) -> str:
    """Convert DateLike input to ISO date string (YYYY-MM-DD)."""
    return to_date(d).isoformat()


def format_year_month(date_input: DateLike) -> str:
    """
    Format date to year-month string format (YYYY-MM).

    Args:
        date_input: Date object, datetime object, or ISO format string

    Returns:
        String in format "YYYY-MM"

    Examples:
        >>> from datetime import date, datetime
        >>> format_year_month(date(2024, 3, 16))
        '2024-03'

        >>> format_year_month("2024-03-16")
        '2024-03'

        >>> format_year_month(datetime(2024, 12, 31, 15, 30))
        '2024-12'
    """
    date_obj = to_date(date_input)
    return date_obj.strftime("%Y-%m")


def generate_date_array(
    date_start: DateLike,
    date_end: DateLike,
    interval: int = 1,
    date_part: DatePart = "DAY",
) -> list[date]:
    """
    Generates a list of dates from date_start to date_end inclusive.
    Equivalent to BigQuery GENERATE_DATE_ARRAY.

    Args:
        date_start: Start date (date/datetime object or ISO format string like "2024-01-01")
        date_end: End date (date/datetime object or ISO format string like "2024-01-05")
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
    date_start = to_date(date_start)
    date_end = to_date(date_end)

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


def get_relative_date_frame(date_part: DatePart = "MONTH", n: int = 0, *, date_from: DateLike | None = None):
    """
    Args:
        date_part: Date part - DAY, WEEK, MONTH, QUARTER, or YEAR (default MONTH)
        n: relative offset (0 = current, <0 = past, >0 = future)
        date_from: Base date to calculate from. If None, uses today's date.
            Can be date/datetime object or ISO format string like "2024-01-15"

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

        >>> # With custom base date
        >>> get_relative_date_frame("MONTH", 0, date_from="2024-06-15")
        ('2024-06-01', '2024-06-30')

        >>> get_relative_date_frame("QUARTER", -1, date_from=date(2024, 6, 15))
        ('2024-01-01', '2024-03-31')

    """
    if date_from is not None:
        # Convert date_from to pendulum datetime
        if isinstance(date_from, str):
            date_base = pendulum.parse(date_from)
        else:
            # date_from is a date object
            date_base = pendulum.instance(date_from)
    else:
        date_base = pendulum.today()

    match date_part:
        case "DAY":
            target = date_base.add(days=n)
            start, end = target.start_of("day"), target.end_of("day")

        case "WEEK":
            target = date_base.add(weeks=n)
            start, end = target.start_of("week"), target.end_of("week")

        case "MONTH":
            target = date_base.add(months=n)
            start, end = target.start_of("month"), target.end_of("month")

        case "QUARTER":
            target = date_base.add(months=3 * n)
            # Calculate quarter manually since pendulum doesn't support "quarter"
            quarter_month = ((target.month - 1) // 3) * 3 + 1  # 1, 4, 7, or 10
            start = target.replace(month=quarter_month, day=1).start_of("month")
            end = target.replace(month=quarter_month + 2, day=1).end_of("month")

        case "YEAR":
            target = date_base.add(years=n)
            start, end = target.start_of("year"), target.end_of("year")

        case _:
            raise ValueError("date_part must be - DAY, WEEK, MONTH, QUARTER, or YEAR")

    return start.to_date_string(), end.to_date_string()


@dataclass(frozen=True, init=False)
class DateRange:
    """Date range with flexible initialization and rich manipulation methods.

    Main class for working with date intervals in ETL workflows. Supports conversion
    to various formats (timestamps, API-specific formats), splitting into chunks,
    and calendar-aware operations.

    Attributes:
        date_start: Start date in YYYY-MM-DD format
        date_end: End date in YYYY-MM-DD format (inclusive)

    Examples:
        >>> # Various initialization patterns
        >>> DateRange()  # Today to today
        DateRange(date_start='2024-12-24', date_end='2024-12-24')

        >>> DateRange("2024-01-01")  # Single date
        DateRange(date_start='2024-01-01', date_end='2024-01-01')

        >>> DateRange("2024-01-01", "2024-01-31")  # Date range
        DateRange(date_start='2024-01-01', date_end='2024-01-31')

        >>> # Rich conversion methods
        >>> dr = DateRange("2024-01-01", "2024-01-07")
        >>> dr.to_fb_time_range()
        {'since': '2024-01-01', 'until': '2024-01-07'}

        >>> dr.split(3)  # Split into 3-day chunks
        [DateRange('2024-01-01', '2024-01-03'), DateRange('2024-01-04', '2024-01-06'), DateRange('2024-01-07', '2024-01-07')]
    """

    date_start: str  # YYYY-MM-DD
    date_end: str  # YYYY-MM-DD

    def __init__(self, date_start: DateLike | None = None, date_end: DateLike | None = None):
        """Initialize DateRange with flexible rules.

        Args:
            date_start: Start date. If None, defaults to today
            date_end: End date. If None, defaults to date_start

        Initialization patterns:
            - DateRange() → today to today
            - DateRange(date) → date to date
            - DateRange(start, end) → start to end
        """
        if date_start is None and date_end is None:
            # DateRange() → today to today
            today = to_date_iso_str(date.today())
            object.__setattr__(self, "date_start", today)
            object.__setattr__(self, "date_end", today)
        elif date_end is None:
            # DateRange(date) → date to date (single day)
            start_str = to_date_iso_str(date_start)
            object.__setattr__(self, "date_start", start_str)
            object.__setattr__(self, "date_end", start_str)
        else:
            # DateRange(start, end) → start to end
            object.__setattr__(self, "date_start", to_date_iso_str(date_start))
            object.__setattr__(self, "date_end", to_date_iso_str(date_end))

    def __str__(self) -> str:
        return f"[{self.date_start} → {self.date_end}]"

    def as_tuple(self) -> tuple[str, str]:
        return self.date_start, self.date_end

    def as_list(self) -> list[str]:
        return [self.date_start, self.date_end]

    def as_dict(self) -> dict:
        return {"date_start": self.date_start, "date_end": self.date_end}

    def format(self, template: str = "{start} -> {end}") -> str:
        return template.format(start=self.date_start, end=self.date_end)

    def to_dict_with_custom_keys(self, key_start: str = "starts_at", key_end: str = "ends_at") -> dict[str, str]:
        """Convert to dict with custom key names.

        Args:
            key_start: Key name for start date (default "starts_at")
            key_end: Key name for end date (default "ends_at")

        Returns:
            Dictionary with custom keys mapping to date strings

        Examples:
            >>> dr = DateRange("2024-01-01", "2024-01-31")
            >>> dr.to_dict_with_custom_keys()
            {'starts_at': '2024-01-01', 'ends_at': '2024-01-31'}

            >>> dr.to_dict_with_custom_keys("from_date", "to_date")
            {'from_date': '2024-01-01', 'to_date': '2024-01-31'}
        """
        return {key_start: self.date_start, key_end: self.date_end}

    def to_fb_time_range(self) -> dict[str, str]:
        """Convert to Facebook Ads API time range format.

        Returns:
            Dictionary with 'since' and 'until' keys

        Examples:
            >>> dr = DateRange("2024-01-01", "2024-01-31")
            >>> dr.to_fb_time_range()
            {'since': '2024-01-01', 'until': '2024-01-31'}
        """
        return {"since": self.date_start, "until": self.date_end}

    def to_reddit_range(self, tz: str | None = None) -> dict[str, str]:
        """Convert to Reddit API timestamp range format.

        Args:
            tz: Timezone name (e.g., 'Asia/Tbilisi'). If None, uses UTC

        Returns:
            Dictionary with 'starts_at' and 'ends_at' UTC timestamps

        Examples:
            >>> dr = DateRange("2024-01-01", "2024-01-02")
            >>> dr.to_reddit_range()
            {'starts_at': '2024-01-01T00:00:00Z', 'ends_at': '2024-01-03T00:00:00Z'}
        """
        result = self.to_timestamps(tz=tz, key_start="starts_at", key_end="ends_at")
        return result

    def to_timestamps(
        self,
        time: str = "00:00:00",
        tz: str | None = None,
        key_start: str = "starts_at",
        key_end: str = "ends_at",
    ) -> dict[str, str]:
        """Convert date range to UTC timestamps in ISO 8601 format.

        End period is automatically extended by 1 day to create inclusive range.
        This is common pattern for APIs that expect timestamp ranges.

        Args:
            time: Time in HH:MM:SS format (default "00:00:00")
            tz: Timezone name (e.g., 'Asia/Tbilisi'). If None, treats as UTC
            key_start: Key name for start timestamp (default "starts_at")
            key_end: Key name for end timestamp (default "ends_at")

        Returns:
            Dictionary with UTC timestamps in ISO format ending with 'Z'

        Logic:
            1. Create timestamps with specified time in specified timezone
            2. Convert to UTC
            3. End date is automatically incremented by 1 day

        Examples:
            >>> dr = DateRange("2024-01-01", "2024-01-02")
            >>> dr.to_timestamps()
            {'starts_at': '2024-01-01T00:00:00Z', 'ends_at': '2024-01-03T00:00:00Z'}

            >>> dr.to_timestamps(time="12:30:00", tz="Europe/Moscow")
            {'starts_at': '2024-01-01T09:30:00Z', 'ends_at': '2024-01-03T09:30:00Z'}
        """
        date_start = to_date(self.date_start)
        date_end = to_date(self.date_end) + timedelta(days=1)

        # Parse time components
        time_parts = time.split(":")
        hour, minute, second = (
            int(time_parts[0]),
            int(time_parts[1]),
            int(time_parts[2]),
        )

        if tz is None:
            # Already UTC - create datetime objects directly in UTC
            dt_start = datetime.combine(
                date_start,
                datetime.min.time().replace(hour=hour, minute=minute, second=second),
                UTC,
            )
            dt_end = datetime.combine(
                date_end,
                datetime.min.time().replace(hour=hour, minute=minute, second=second),
                UTC,
            )
        else:
            # Create datetime in specified timezone and convert to UTC
            local_tz = ZoneInfo(tz)
            dt_start = datetime.combine(
                date_start,
                datetime.min.time().replace(hour=hour, minute=minute, second=second),
                local_tz,
            ).astimezone(UTC)
            dt_end = datetime.combine(
                date_end,
                datetime.min.time().replace(hour=hour, minute=minute, second=second),
                local_tz,
            ).astimezone(UTC)

        return {
            key_start: dt_start.isoformat().replace("+00:00", "Z"),
            key_end: dt_end.isoformat().replace("+00:00", "Z"),
        }

    def split(self, chunk_days: int) -> list[DateRange]:
        """Split date range into chunks of specified size.

        Args:
            chunk_days: Size of each chunk in days (must be >= 1)

        Returns:
            List of DateRange objects covering the original range

        Raises:
            ValueError: If chunk_days < 1

        Examples:
            >>> dr = DateRange("2024-01-01", "2024-01-10")
            >>> chunks = dr.split(3)
            >>> [str(c) for c in chunks]
            ['[2024-01-01 → 2024-01-03]', '[2024-01-04 → 2024-01-06]', '[2024-01-07 → 2024-01-09]', '[2024-01-10 → 2024-01-10]']

            >>> dr.split(7)  # Weekly chunks
            [DateRange('2024-01-01', '2024-01-07'), DateRange('2024-01-08', '2024-01-10')]
        """
        ranges: list[DateRange] = []

        if chunk_days < 1:
            raise ValueError("chunk_days must be >= 1")

        date_start = to_date(self.date_start)
        date_end = to_date(self.date_end)

        date_start_current = date_start

        while date_start_current <= date_end:
            # Take either end of original range or current start + chunk size
            # -1 day because chunk_days=7 means 7 days inclusive (Mon-Sun), not 8
            date_end_current = min(date_end, date_start_current + timedelta(days=chunk_days - 1))
            ranges.append(DateRange(to_date_iso_str(date_start_current), to_date_iso_str(date_end_current)))

            # +1 day so next chunk starts on the day after current chunk ends
            date_start_current = date_end_current + timedelta(days=1)

        return ranges

    @staticmethod
    def around_date(
        *,
        date_anchor: DateLike | None = None,
        days_lookback: int | None = None,  # None -> 0
        days_lookforward: int | None = None,  # None -> 0
    ) -> DateRange:
        """Create date range around anchor date with lookback/forward windows.

        Args:
            date_anchor: Anchor date (default: today)
            days_lookback: Days to look back from anchor (default: 0)
            days_lookforward: Days to look forward from anchor (default: 0)

        Returns:
            DateRange spanning the calculated window

        Rules:
            - Only lookback: [anchor - lookback, anchor]
            - Only lookforward: [anchor, anchor + lookforward]
            - Both specified: [anchor - lookback, anchor + lookforward]
            - Neither specified: [anchor, anchor]
            - All values must be >= 0

        Raises:
            ValueError: If lookback or lookforward < 0

        Examples:
            >>> # 7 days back from today
            >>> dr = DateRange.around_date(days_lookback=7)
            >>> # [2024-12-17 → 2024-12-24] (if today is 2024-12-24)

            >>> # 3 days forward from specific date
            >>> dr = DateRange.around_date(date_anchor="2024-01-01", days_lookforward=3)
            >>> str(dr)
            '[2024-01-01 → 2024-01-04]'

            >>> # Window around date: 2 days back, 1 day forward
            >>> dr = DateRange.around_date(date_anchor="2024-06-15", days_lookback=2, days_lookforward=1)
            >>> str(dr)
            '[2024-06-13 → 2024-06-16]'
        """
        # Set anchor date
        date_anchor = date_anchor or date.today()
        date_anchor = to_date(date_anchor)

        # Normalize parameters
        lb = 0 if days_lookback is None else int(days_lookback)
        lf = 0 if days_lookforward is None else int(days_lookforward)
        if lb < 0 or lf < 0:
            raise ValueError("days_lookback/days_lookforward must be >= 0")

        date_start = date_anchor - timedelta(days=lb)
        date_end = date_anchor + timedelta(days=lf)

        return DateRange(to_date_iso_str(date_start), to_date_iso_str(date_end))

    def contains(self, date: DateLike) -> bool:
        """Check if date is within the range."""
        date_str = to_date_iso_str(date)
        return self.date_start <= date_str <= self.date_end

    def overlaps(self, other: DateRange) -> bool:
        """Check if this range overlaps with another range."""
        return not (self.date_end < other.date_start or self.date_start > other.date_end)

    def days_count(self) -> int:
        """Count number of days in range (inclusive)."""
        start = to_date(self.date_start)
        end = to_date(self.date_end)
        return (end - start).days + 1

    def extend_by_days(self, start_days: int, end_days: int) -> DateRange:
        """Extend range: start_days backward, end_days forward."""
        start = to_date(self.date_start) - timedelta(days=start_days)
        end = to_date(self.date_end) + timedelta(days=end_days)
        return DateRange(to_date_iso_str(start), to_date_iso_str(end))

    def shift_by_days(self, days: int) -> DateRange:
        """Shift entire range by N days (+ forward, - backward)."""
        start = to_date(self.date_start) + timedelta(days=days)
        end = to_date(self.date_end) + timedelta(days=days)
        return DateRange(to_date_iso_str(start), to_date_iso_str(end))

    def extend_to_week_bounds(self) -> DateRange:
        """Extend to week boundaries (Mon-Sun)."""
        start = to_date(self.date_start)
        end = to_date(self.date_end)

        # Find Monday of start week
        week_start = start - timedelta(days=start.weekday())
        # Find Sunday of end week
        week_end = end + timedelta(days=6 - end.weekday())

        return DateRange(to_date_iso_str(week_start), to_date_iso_str(week_end))

    def extend_to_month_bounds(self) -> DateRange:
        """Extend to month boundaries (1st - last day)."""
        start = to_date(self.date_start)
        end = to_date(self.date_end)

        # First day of start month
        month_start = start.replace(day=1)
        # Last day of end month
        if end.month == 12:
            next_month = end.replace(year=end.year + 1, month=1, day=1)
        else:
            next_month = end.replace(month=end.month + 1, day=1)
        month_end = next_month - timedelta(days=1)

        return DateRange(to_date_iso_str(month_start), to_date_iso_str(month_end))

    @staticmethod
    def single_calendar_period(date_part: DatePart, offset: int = 0, date_anchor: DateLike | None = None) -> DateRange:
        """Create single calendar period with offset.

        Args:
            date_part: Type of period - "WEEK", "MONTH", "QUARTER", "YEAR"
            offset: Period offset (0=current, -1=previous, +1=next)
            date_anchor: Reference date (default: today)

        Returns:
            DateRange for the specified calendar period

        Examples:
            >>> # Current month
            >>> dr = DateRange.single_calendar_period("MONTH", offset=0)

            >>> # Previous quarter from specific date
            >>> dr = DateRange.single_calendar_period("QUARTER", offset=-1, date_anchor="2024-06-15")
        """
        date_anchor = date_anchor or date.today()
        date_start_str, date_end_str = get_relative_date_frame(date_part, offset, date_from=date_anchor)
        return DateRange(date_start_str, date_end_str)


class DateRanges:
    """Generator for multiple date ranges with different patterns.

    Provides methods to generate date ranges for common ETL scenarios:
    1. calendar_periods() - Calendar-aligned periods (weeks, months) for consistent reporting
    2. split_lookback_period() - Chunked lookback periods for backfill operations
    3. offset_range_buckets() - Custom offset ranges for flexible period selection

    All methods return lists of DateRange objects that can be easily converted
    to API-specific formats or used for data processing loops.

    Examples:
        >>> dr = DateRanges()
        >>> # Last 4 weeks ending today
        >>> weeks = dr.calendar_periods("WEEK", count=4)
        >>> len(weeks)
        4

        >>> # Split 30 days into 7-day chunks
        >>> chunks = dr.split_lookback_period(total_days=30, chunk_days=7)
        >>> len(chunks)  # 5 chunks: 4 full weeks + 2 remaining days
        5
    """

    def __init__(self):
        """Initialize DateRanges generator."""
        pass

    def calendar_periods(
        self,
        date_part: DatePart = "WEEK",
        count: int = 4,
        date_end: DateLike | None = None,
        trim_last_period: bool = True,
    ) -> list[DateRange]:
        """Generate calendar-aligned periods (weeks, months, etc.).

        Creates stable, calendar-aligned periods that are consistent across runs.
        Useful for reporting and analytics where period boundaries matter.

        Args:
            date_part: Type of period - "WEEK", "MONTH", "QUARTER", "YEAR"
            count: Number of periods to generate
            date_end: End date for range calculation (default: today)
            trim_last_period: Whether to trim last period to date_end (default: True)

        Returns:
            List of DateRange objects in reverse chronological order
            (most recent first)

        Examples:
            >>> dr = DateRanges()
            >>> # Last 3 weeks ending today
            >>> weeks = dr.calendar_periods("WEEK", count=3)
            >>> # [current_week, previous_week, week_before_that]

            >>> # Last 6 months ending on specific date
            >>> months = dr.calendar_periods("MONTH", count=6, date_end="2024-06-15")
            >>> len(months)
            6

            >>> # Don't trim last period (show full calendar periods)
            >>> quarters = dr.calendar_periods("QUARTER", count=2, trim_last_period=False)
        """
        ranges: list[DateRange] = []

        date_end_str = to_date_iso_str(date_end or date.today())

        for i in range(count):
            offset = -i
            date_start_str, date_end_period_str = get_relative_date_frame(date_part, offset, date_from=date_end)

            # If period end is beyond date_end, optionally trim it
            if trim_last_period and date_end_period_str > date_end_str:
                date_end_period_str = date_end_str

            ranges.append(DateRange(date_start_str, date_end_period_str))

        return ranges

    def offset_range_buckets(
        self,
        date_part: DatePart = "WEEK",
        offset_start: int = 0,
        offset_end: int = -3,
        date_end: DateLike | None = None,
    ) -> list[DateRange]:
        """Generate periods for a range of offsets.

        More flexible than calendar_periods() - allows specifying exact offset range
        instead of just count. Useful for custom period selections.

        Args:
            date_part: Type of period - "WEEK", "MONTH", "QUARTER", "YEAR"
            offset_start: Starting offset (e.g., 0 for current period)
            offset_end: Ending offset (e.g., -3 for 3 periods back)
            date_end: Reference date for calculations (default: today)

        Returns:
            List of DateRange objects covering the offset range

        Examples:
            >>> dr = DateRanges()
            >>> # Current period through 3 periods back (4 total)
            >>> ranges = dr.offset_range_buckets("WEEK", offset_start=0, offset_end=-3)
            >>> len(ranges)  # periods 0, -1, -2, -3
            4

            >>> # Specific historical range: 4th through 6th periods back
            >>> historical = dr.offset_range_buckets("MONTH", offset_start=-4, offset_end=-6)
            >>> len(historical)  # periods -4, -5, -6
            3
        """
        ranges: list[DateRange] = []

        date_end_str = to_date_iso_str(date_end or date.today())

        for offset in range(offset_start, offset_end - 1, -1):
            date_start_str, date_end_period_str = get_relative_date_frame(date_part, offset, date_from=date_end)

            # If period end exceeds date_end, trim it
            if date_end_period_str > date_end_str:
                date_end_period_str = date_end_str

            ranges.append(DateRange(date_start_str, date_end_period_str))

        return ranges

    def split_lookback_period(
        self,
        total_days: int,
        chunk_days: int,
        date_end: DateLike | None = None,
    ) -> list[DateRange]:
        """Split a lookback period into fixed-size chunks.

        Useful for backfill operations where you need to process a long historical
        period in manageable chunks. Chunks are generated in reverse chronological
        order (most recent first).

        Args:
            total_days: Total number of days to cover
            chunk_days: Size of each chunk in days (must be >= 1)
            date_end: Reference end date (default: today)

        Returns:
            List of DateRange objects covering the lookback period

        Raises:
            ValueError: If chunk_days < 1

        Examples:
            >>> dr = DateRanges()
            >>> # Split last 30 days into 7-day chunks
            >>> chunks = dr.split_lookback_period(total_days=30, chunk_days=7)
            >>> len(chunks)  # 5 chunks: 4 full weeks + 2 remaining days
            5

            >>> # Process last 90 days in monthly chunks
            >>> monthly = dr.split_lookback_period(total_days=90, chunk_days=30, date_end="2024-12-31")
            >>> # [Dec 2-31, Nov 2-Dec 1, Oct 3-Nov 1]
        """
        ranges: list[DateRange] = []

        if chunk_days < 1:
            raise ValueError("chunk_days must be >= 1")
        date_end = to_date(date_end or date.today())

        date_end_current = date_end
        date_start_total = date_end_current - timedelta(days=total_days - 1)

        while date_end_current >= date_start_total:
            # Calculate chunk start: either total start or chunk_days back from current end
            date_start_current = max(date_start_total, date_end_current - timedelta(days=chunk_days - 1))
            ranges.append(DateRange(to_date_iso_str(date_start_current), to_date_iso_str(date_end_current)))
            # Move to previous chunk: end becomes start-1 of current chunk
            date_end_current = date_start_current - timedelta(days=1)
        return ranges
