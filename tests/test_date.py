from datetime import UTC, date, datetime

import pytest

from etlutil.date import (
    DateRange,
    DateRanges,
    format_year_month,
    generate_date_array,
    get_relative_date_frame,
    to_date,
    to_date_iso_str,
)


# ==================== FIXTURES ====================
@pytest.fixture
def sample_dates():
    """Common date fixtures for testing."""
    return {
        "start_date": "2024-01-01",
        "end_date": "2024-01-05",
        "leap_year_start": "2024-02-28",
        "leap_year_end": "2024-03-01",
        "month_end_start": "2024-01-31",
        "month_end_end": "2024-03-31",
        "year_start": "2024-01-01",
        "year_end": "2028-01-01",
    }


@pytest.fixture
def expected_results():
    """Expected results for common test cases."""
    return {
        "basic_range": [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4), date(2024, 1, 5)],
        "three_days": [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)],
        "leap_year_range": [date(2024, 2, 28), date(2024, 2, 29), date(2024, 3, 1)],
        "month_end_range": [date(2024, 1, 31), date(2024, 2, 29), date(2024, 3, 31)],
        "year_range": [date(2024, 1, 1), date(2025, 1, 1), date(2026, 1, 1), date(2027, 1, 1), date(2028, 1, 1)],
    }


# ==================== TO_DATE AND TO_DATE_ISO_STR TESTS ====================
class TestToDate:
    """Test cases for to_date utility function."""

    def test_date_input_unchanged(self):
        """Test that date objects are returned unchanged."""
        d = date(2024, 1, 15)
        result = to_date(d)
        assert result == d
        assert result is d  # Same object reference

    def test_datetime_extracts_date(self):
        """Test that datetime objects extract date part."""
        dt = datetime(2024, 1, 15, 12, 30, 45)
        result = to_date(dt)
        expected = date(2024, 1, 15)
        assert result == expected
        assert isinstance(result, date)
        assert not isinstance(result, datetime)

    def test_string_parsing_basic(self):
        """Test basic ISO string parsing."""
        result = to_date("2024-01-15")
        expected = date(2024, 1, 15)
        assert result == expected

    def test_string_parsing_edge_cases(self):
        """Test string parsing edge cases."""
        # Leap year
        assert to_date("2024-02-29") == date(2024, 2, 29)
        # End of year
        assert to_date("2024-12-31") == date(2024, 12, 31)
        # Start of year
        assert to_date("2024-01-01") == date(2024, 1, 1)

    def test_invalid_date_strings_raise_errors(self):
        """Test that invalid date strings raise ValueError."""
        invalid_dates = [
            "not-a-date",
            "2024-13-01",  # Invalid month
            "2024-02-30",  # Invalid day
            "24-01-01",  # Wrong format
            "",  # Empty string
            "2024-1-1",  # Missing zero padding
        ]

        for invalid in invalid_dates:
            with pytest.raises(ValueError):
                to_date(invalid)

    def test_datetime_with_timezone_info(self):
        """Test datetime with timezone info extracts date correctly."""
        from datetime import timedelta, timezone

        # UTC datetime
        dt_utc = datetime(2024, 1, 15, 12, 30, tzinfo=UTC)
        assert to_date(dt_utc) == date(2024, 1, 15)

        # Different timezone
        tz_offset = timezone(timedelta(hours=3))
        dt_tz = datetime(2024, 1, 15, 12, 30, tzinfo=tz_offset)
        assert to_date(dt_tz) == date(2024, 1, 15)

    @pytest.mark.parametrize(
        "year,month,day",
        [
            (2024, 1, 1),  # Start of year
            (2024, 12, 31),  # End of year
            (2024, 2, 29),  # Leap year day
            (2023, 2, 28),  # Non-leap year Feb end
            (2024, 6, 15),  # Mid year
        ],
    )
    def test_date_consistency_across_types(self, year, month, day):
        """Test that all input types produce same date."""
        expected = date(year, month, day)
        dt = datetime(year, month, day, 14, 30, 45)
        iso_str = f"{year:04d}-{month:02d}-{day:02d}"

        assert to_date(expected) == expected
        assert to_date(dt) == expected
        assert to_date(iso_str) == expected


class TestToDateIsoStr:
    """Test cases for to_date_iso_str utility function."""

    def test_date_to_iso_string(self):
        """Test date object to ISO string conversion."""
        d = date(2024, 1, 15)
        result = to_date_iso_str(d)
        assert result == "2024-01-15"

    def test_datetime_to_iso_string(self):
        """Test datetime object to ISO string conversion."""
        dt = datetime(2024, 1, 15, 12, 30, 45)
        result = to_date_iso_str(dt)
        assert result == "2024-01-15"

    def test_string_passthrough_idempotent(self):
        """Test that valid ISO strings pass through unchanged."""
        iso_str = "2024-01-15"
        result = to_date_iso_str(iso_str)
        assert result == iso_str

    def test_consistency_across_input_types(self):
        """Test that all input types produce same ISO string."""
        dt = datetime(2024, 3, 15, 12, 30)
        d = date(2024, 3, 15)
        s = "2024-03-15"

        expected = "2024-03-15"
        assert to_date_iso_str(dt) == expected
        assert to_date_iso_str(d) == expected
        assert to_date_iso_str(s) == expected

    def test_timezone_datetime_extraction(self):
        """Test that timezone info is ignored, only date part extracted."""

        dt_utc = datetime(2024, 1, 15, 23, 59, tzinfo=UTC)
        result = to_date_iso_str(dt_utc)
        assert result == "2024-01-15"

    @pytest.mark.parametrize(
        "input_date,expected",
        [
            (date(2024, 1, 1), "2024-01-01"),
            (date(2024, 12, 31), "2024-12-31"),
            (date(2024, 2, 29), "2024-02-29"),  # Leap year
            (datetime(2024, 6, 15, 14, 30), "2024-06-15"),
            ("2024-03-15", "2024-03-15"),
        ],
    )
    def test_parametrized_conversions(self, input_date, expected):
        """Test various input/output combinations."""
        result = to_date_iso_str(input_date)
        assert result == expected

    def test_roundtrip_consistency(self):
        """Test that to_date(to_date_iso_str(d)) == d for date objects."""
        original_dates = [
            date(2024, 1, 1),
            date(2024, 2, 29),  # Leap year
            date(2024, 12, 31),
            date(2023, 2, 28),  # Non-leap year
        ]

        for d in original_dates:
            iso_str = to_date_iso_str(d)
            roundtrip = to_date(iso_str)
            assert roundtrip == d

    def test_invalid_inputs_propagate_errors(self):
        """Test that invalid inputs raise appropriate errors."""
        with pytest.raises(ValueError):
            to_date_iso_str("invalid-date")


# ==================== GENERATE_DATE_ARRAY TESTS ====================
class TestGenerateDateArray:
    """Test cases for generate_date_array function using fixtures and parametrization."""

    # ==================== BASIC FUNCTIONALITY ====================
    def test_basic_date_range(self, sample_dates, expected_results):
        """Test basic date range with default parameters."""
        result = generate_date_array(sample_dates["start_date"], sample_dates["end_date"])
        assert result == expected_results["basic_range"]

    def test_date_objects_input(self, expected_results):
        """Test with date objects instead of strings."""
        result = generate_date_array(date(2024, 1, 1), date(2024, 1, 3))
        assert result == expected_results["three_days"]

    def test_mixed_input_types(self, expected_results):
        """Test with mixed input types (string and date object)."""
        result = generate_date_array("2024-01-01", date(2024, 1, 3))
        assert result == expected_results["three_days"]

    # ==================== INTERVAL TYPES ====================
    @pytest.mark.parametrize(
        "start_date, end_date, interval, interval_type, expected",
        [
            (
                "2024-01-01",
                "2024-01-10",
                2,
                "DAY",
                [date(2024, 1, 1), date(2024, 1, 3), date(2024, 1, 5), date(2024, 1, 7), date(2024, 1, 9)],
            ),
            (
                "2024-01-01",
                "2024-01-22",
                1,
                "WEEK",
                [date(2024, 1, 1), date(2024, 1, 8), date(2024, 1, 15), date(2024, 1, 22)],
            ),
            (
                "2024-01-01",
                "2024-06-01",
                1,
                "MONTH",
                [
                    date(2024, 1, 1),
                    date(2024, 2, 1),
                    date(2024, 3, 1),
                    date(2024, 4, 1),
                    date(2024, 5, 1),
                    date(2024, 6, 1),
                ],
            ),
            (
                "2024-01-01",
                "2024-12-01",
                1,
                "QUARTER",
                [date(2024, 1, 1), date(2024, 4, 1), date(2024, 7, 1), date(2024, 10, 1)],
            ),
            (
                "2024-01-01",
                "2024-07-01",
                2,
                "MONTH",
                [date(2024, 1, 1), date(2024, 3, 1), date(2024, 5, 1), date(2024, 7, 1)],
            ),
        ],
    )
    def test_interval_types(self, start_date, end_date, interval, interval_type, expected):
        """Test different interval types with parametrization."""
        result = generate_date_array(start_date, end_date, interval, interval_type)
        assert result == expected

    def test_year_interval(self, sample_dates, expected_results):
        """Test with year interval."""
        result = generate_date_array(sample_dates["year_start"], sample_dates["year_end"], 1, "YEAR")
        assert result == expected_results["year_range"]

    # ==================== EDGE CASES ====================
    @pytest.mark.parametrize(
        "start_date, end_date, expected",
        [
            ("2024-01-05", "2024-01-01", []),  # Empty range
            ("2024-01-01", "2024-01-01", [date(2024, 1, 1)]),  # Single date
        ],
    )
    def test_edge_cases(self, start_date, end_date, expected):
        """Test edge cases with parametrization."""
        result = generate_date_array(start_date, end_date)
        assert result == expected

    def test_zero_interval_returns_empty(self, sample_dates):
        """Test that zero interval returns empty list."""
        result = generate_date_array(sample_dates["start_date"], sample_dates["end_date"], 0)
        assert result == []

    def test_invalid_date_format(self, sample_dates):
        """Test that invalid date format raises ValueError."""
        with pytest.raises(ValueError):
            generate_date_array("invalid-date", sample_dates["end_date"])

    # ==================== LEAP YEAR HANDLING ====================
    def test_leap_year_handling(self, sample_dates, expected_results):
        """Test handling of leap years."""
        result = generate_date_array(sample_dates["leap_year_start"], sample_dates["leap_year_end"])
        assert result == expected_results["leap_year_range"]

    def test_month_end_handling(self, sample_dates, expected_results):
        """Test handling of month end dates."""
        result = generate_date_array(sample_dates["month_end_start"], sample_dates["month_end_end"], 1, "MONTH")
        assert result == expected_results["month_end_range"]

    # ==================== LARGE INTERVALS ====================
    @pytest.mark.parametrize(
        "start_date, end_date, interval, interval_type, expected",
        [
            (
                "2024-01-01",
                "2024-12-31",
                30,
                "DAY",
                [
                    date(2024, 1, 1),
                    date(2024, 1, 31),
                    date(2024, 3, 1),
                    date(2024, 3, 31),
                    date(2024, 4, 30),
                    date(2024, 5, 30),
                    date(2024, 6, 29),
                    date(2024, 7, 29),
                    date(2024, 8, 28),
                    date(2024, 9, 27),
                    date(2024, 10, 27),
                    date(2024, 11, 26),
                    date(2024, 12, 26),
                ],
            ),
        ],
    )
    def test_large_interval(self, start_date, end_date, interval, interval_type, expected):
        """Test with large interval values."""
        result = generate_date_array(start_date, end_date, interval, interval_type)
        assert result == expected

    # ==================== NEGATIVE INTERVALS ====================
    @pytest.mark.parametrize(
        "start_date, end_date, interval, interval_type, expected",
        [
            (
                "2024-01-05",
                "2024-01-01",
                -1,
                "DAY",
                [date(2024, 1, 5), date(2024, 1, 4), date(2024, 1, 3), date(2024, 1, 2), date(2024, 1, 1)],
            ),
            (
                "2024-01-22",
                "2024-01-01",
                -1,
                "WEEK",
                [date(2024, 1, 22), date(2024, 1, 15), date(2024, 1, 8), date(2024, 1, 1)],
            ),
            (
                "2024-06-01",
                "2024-01-01",
                -1,
                "MONTH",
                [
                    date(2024, 6, 1),
                    date(2024, 5, 1),
                    date(2024, 4, 1),
                    date(2024, 3, 1),
                    date(2024, 2, 1),
                    date(2024, 1, 1),
                ],
            ),
            (
                "2024-12-01",
                "2024-01-01",
                -1,
                "QUARTER",
                [date(2024, 12, 1), date(2024, 9, 1), date(2024, 6, 1), date(2024, 3, 1)],
            ),
            (
                "2028-01-01",
                "2024-01-01",
                -1,
                "YEAR",
                [date(2028, 1, 1), date(2027, 1, 1), date(2026, 1, 1), date(2025, 1, 1), date(2024, 1, 1)],
            ),
            (
                "2024-01-10",
                "2024-01-01",
                -2,
                "DAY",
                [date(2024, 1, 10), date(2024, 1, 8), date(2024, 1, 6), date(2024, 1, 4), date(2024, 1, 2)],
            ),
            (
                "2024-12-01",
                "2024-01-01",
                -2,
                "MONTH",
                [
                    date(2024, 12, 1),
                    date(2024, 10, 1),
                    date(2024, 8, 1),
                    date(2024, 6, 1),
                    date(2024, 4, 1),
                    date(2024, 2, 1),
                ],
            ),
        ],
    )
    def test_negative_intervals(self, start_date, end_date, interval, interval_type, expected):
        """Test negative intervals with parametrization."""
        result = generate_date_array(start_date, end_date, interval, interval_type)
        assert result == expected

    @pytest.mark.parametrize(
        "start_date, end_date, interval, interval_type, expected",
        [
            ("2024-01-01", "2024-01-01", -1, "DAY", [date(2024, 1, 1)]),  # Same start and end date
            ("2024-01-01", "2024-01-05", -1, "DAY", []),  # Start date before end date with negative interval
        ],
    )
    def test_negative_interval_edge_cases(self, start_date, end_date, interval, interval_type, expected):
        """Test negative interval edge cases."""
        result = generate_date_array(start_date, end_date, interval, interval_type)
        assert result == expected

    # ==================== FULL YEAR RANGE TESTS ====================
    def test_leap_year_full_range(self):
        """Test that leap year (2024) has exactly 366 days from start to end."""
        result = generate_date_array("2024-01-01", "2024-12-31")
        assert len(result) == 366  # 2024 is a leap year
        assert result[0] == date(2024, 1, 1)
        assert result[-1] == date(2024, 12, 31)

    def test_regular_year_full_range(self):
        """Test that regular year (2023) has exactly 365 days from start to end."""
        result = generate_date_array("2023-01-01", "2023-12-31")
        assert len(result) == 365  # 2023 is not a leap year
        assert result[0] == date(2023, 1, 1)
        assert result[-1] == date(2023, 12, 31)

    @pytest.mark.parametrize(
        "year, expected_days",
        [
            (2020, 366),  # Leap year
            (2021, 365),  # Regular year
            (2022, 365),  # Regular year
            (2023, 365),  # Regular year
            (2024, 366),  # Leap year
            (2025, 365),  # Regular year
        ],
    )
    def test_year_lengths(self, year, expected_days):
        """Test that different years have correct number of days."""
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        result = generate_date_array(start_date, end_date)
        assert len(result) == expected_days
        assert result[0] == date(year, 1, 1)
        assert result[-1] == date(year, 12, 31)


# ==================== FORMAT_YEAR_MONTH TESTS ====================
class TestFormatYearMonth:
    """Test cases for format_year_month function using fixtures and parametrization."""

    # ==================== FIXTURES ====================
    @pytest.fixture
    def sample_dates_for_formatting(self):
        """Sample dates for formatting tests."""
        return {
            "basic_date": date(2024, 3, 16),
            "single_digit_month": date(2024, 1, 15),
            "double_digit_month": date(2024, 12, 31),
            "leap_year_feb": date(2024, 2, 29),
            "non_leap_year_feb": date(2023, 2, 28),
            "first_day": date(2024, 5, 1),
            "middle_day": date(2024, 8, 15),
        }

    @pytest.fixture
    def expected_formatted_results(self):
        """Expected formatted results."""
        return {
            "basic": "2024-03",
            "single_digit": "2024-01",
            "double_digit": "2024-12",
            "leap_year": "2024-02",
            "non_leap_year": "2023-02",
            "first_day": "2024-05",
            "middle_day": "2024-08",
        }

    # ==================== BASIC FUNCTIONALITY ====================
    def test_basic_date_object(self, sample_dates_for_formatting, expected_formatted_results):
        """Test with date object."""
        result = format_year_month(sample_dates_for_formatting["basic_date"])
        assert result == expected_formatted_results["basic"]

    def test_date_string_input(self, expected_formatted_results):
        """Test with date string."""
        result = format_year_month("2024-03-16")
        assert result == expected_formatted_results["basic"]

    # ==================== MONTH FORMATTING ====================
    def test_single_digit_month(self, sample_dates_for_formatting, expected_formatted_results):
        """Test with single digit month (should add leading zero)."""
        result = format_year_month(sample_dates_for_formatting["single_digit_month"])
        assert result == expected_formatted_results["single_digit"]

    def test_double_digit_month(self, sample_dates_for_formatting, expected_formatted_results):
        """Test with double digit month."""
        result = format_year_month(sample_dates_for_formatting["double_digit_month"])
        assert result == expected_formatted_results["double_digit"]

    @pytest.mark.parametrize(
        "input_date, expected",
        [
            (date(2023, 6, 10), "2023-06"),
            (date(2025, 11, 25), "2025-11"),
        ],
    )
    def test_different_years(self, input_date, expected):
        """Test with different years using parametrization."""
        result = format_year_month(input_date)
        assert result == expected

    # ==================== EDGE CASES ====================
    @pytest.mark.parametrize(
        "input_date, expected",
        [
            (date(2024, 5, 1), "2024-05"),  # First day of month
            (date(2024, 2, 29), "2024-02"),  # Last day of month (leap year)
            (date(2024, 8, 15), "2024-08"),  # Middle of month
        ],
    )
    def test_edge_cases_days(self, input_date, expected):
        """Test edge cases with different days of month."""
        result = format_year_month(input_date)
        assert result == expected

    # ==================== FEBRUARY HANDLING ====================
    def test_leap_year_february(self, sample_dates_for_formatting, expected_formatted_results):
        """Test February in leap year."""
        result = format_year_month(sample_dates_for_formatting["leap_year_feb"])
        assert result == expected_formatted_results["leap_year"]

    def test_non_leap_year_february(self, sample_dates_for_formatting, expected_formatted_results):
        """Test February in non-leap year."""
        result = format_year_month(sample_dates_for_formatting["non_leap_year_feb"])
        assert result == expected_formatted_results["non_leap_year"]

    @pytest.mark.parametrize(
        "date_string, expected",
        [
            ("2024-05-01", "2024-05"),  # First day of month
            ("2024-12-31", "2024-12"),  # Last day of month
            ("2024-02-29", "2024-02"),  # Leap year February
        ],
    )
    def test_string_edge_cases(self, date_string, expected):
        """Test string input edge cases."""
        result = format_year_month(date_string)
        assert result == expected

    # ==================== ERROR HANDLING ====================
    @pytest.mark.parametrize(
        "invalid_date",
        [
            "invalid-date",
            "2024-13-01",  # Invalid month
            "2024-02-30",  # Invalid day for February
        ],
    )
    def test_invalid_date_string(self, invalid_date):
        """Test that invalid date string raises ValueError."""
        with pytest.raises(ValueError):
            format_year_month(invalid_date)


# ==================== GET_RELATIVE_DATE_FRAME TESTS ====================
class TestGetRelativeDateFrame:
    """Test cases for get_relative_date_frame function using fixtures and parametrization."""

    # ==================== FIXTURES ====================
    @pytest.fixture
    def mock_today(self, monkeypatch):
        """Mock pendulum.today() to return a fixed date for consistent testing."""
        import pendulum

        # Mock today to be 2024-06-15 (middle of year, middle of month, Saturday)
        fixed_today = pendulum.parse("2024-06-15T12:00:00")

        def mock_today_func():
            return fixed_today

        monkeypatch.setattr(pendulum, "today", mock_today_func)
        return fixed_today

    @pytest.fixture
    def expected_current_periods(self):
        """Expected results for current periods (n=0)."""
        return {
            "DAY": ("2024-06-15", "2024-06-15"),
            "WEEK": ("2024-06-10", "2024-06-16"),  # Monday to Sunday
            "MONTH": ("2024-06-01", "2024-06-30"),
            "QUARTER": ("2024-04-01", "2024-06-30"),  # Q2
            "YEAR": ("2024-01-01", "2024-12-31"),
        }

    # ==================== BASIC FUNCTIONALITY ====================
    def test_current_periods(self, mock_today, expected_current_periods):
        """Test current periods (n=0) for all date parts."""
        for date_part, expected in expected_current_periods.items():
            result = get_relative_date_frame(date_part, 0)
            assert result == expected, f"Failed for {date_part}"

    @pytest.mark.parametrize(
        "date_part, n, expected",
        [
            # Previous periods (n=-1)
            ("DAY", -1, ("2024-06-14", "2024-06-14")),
            ("WEEK", -1, ("2024-06-03", "2024-06-09")),
            ("MONTH", -1, ("2024-05-01", "2024-05-31")),
            ("QUARTER", -1, ("2024-01-01", "2024-03-31")),  # Q1
            ("YEAR", -1, ("2023-01-01", "2023-12-31")),
            # Next periods (n=1)
            ("DAY", 1, ("2024-06-16", "2024-06-16")),
            ("WEEK", 1, ("2024-06-17", "2024-06-23")),
            ("MONTH", 1, ("2024-07-01", "2024-07-31")),
            ("QUARTER", 1, ("2024-07-01", "2024-09-30")),  # Q3
            ("YEAR", 1, ("2025-01-01", "2025-12-31")),
        ],
    )
    def test_relative_periods(self, mock_today, date_part, n, expected):
        """Test relative periods with parametrization."""
        result = get_relative_date_frame(date_part, n)
        assert result == expected

    # ==================== MULTIPLE PERIODS ====================
    @pytest.mark.parametrize(
        "date_part, n, expected",
        [
            # Multiple previous periods
            ("DAY", -7, ("2024-06-08", "2024-06-08")),
            ("WEEK", -4, ("2024-05-13", "2024-05-19")),
            ("MONTH", -6, ("2023-12-01", "2023-12-31")),
            ("QUARTER", -2, ("2023-10-01", "2023-12-31")),  # Q4 2023
            ("YEAR", -3, ("2021-01-01", "2021-12-31")),
            # Multiple next periods
            ("DAY", 10, ("2024-06-25", "2024-06-25")),
            ("WEEK", 8, ("2024-08-05", "2024-08-11")),
            ("MONTH", 12, ("2025-06-01", "2025-06-30")),
            ("QUARTER", 3, ("2025-01-01", "2025-03-31")),  # Q1 2025
            ("YEAR", 5, ("2029-01-01", "2029-12-31")),
        ],
    )
    def test_multiple_periods(self, mock_today, date_part, n, expected):
        """Test multiple periods forward and backward."""
        result = get_relative_date_frame(date_part, n)
        assert result == expected

    # ==================== QUARTER SPECIFIC TESTS ====================
    @pytest.mark.parametrize(
        "n, expected_quarter, expected_range",
        [
            (-1, "Q1", ("2024-01-01", "2024-03-31")),
            (0, "Q2", ("2024-04-01", "2024-06-30")),
            (1, "Q3", ("2024-07-01", "2024-09-30")),
            (2, "Q4", ("2024-10-01", "2024-12-31")),
            (4, "Q2_2025", ("2025-04-01", "2025-06-30")),  # Same quarter next year
            (-4, "Q2_2023", ("2023-04-01", "2023-06-30")),  # Same quarter previous year
        ],
    )
    def test_quarter_boundaries(self, mock_today, n, expected_quarter, expected_range):
        """Test quarter boundaries and transitions."""
        result = get_relative_date_frame("QUARTER", n)
        assert result == expected_range, f"Failed for {expected_quarter}"

    # ==================== YEAR BOUNDARY TESTS ====================
    @pytest.mark.parametrize(
        "date_part, n, expected",
        [
            # Cross year boundaries
            ("MONTH", 6, ("2024-12-01", "2024-12-31")),  # December 2024
            ("MONTH", 7, ("2025-01-01", "2025-01-31")),  # January 2025
            ("MONTH", -6, ("2023-12-01", "2023-12-31")),  # December 2023
            ("MONTH", -7, ("2023-11-01", "2023-11-30")),  # November 2023
        ],
    )
    def test_year_boundaries(self, mock_today, date_part, n, expected):
        """Test crossing year boundaries."""
        result = get_relative_date_frame(date_part, n)
        assert result == expected

    # ==================== LEAP YEAR HANDLING ====================
    def test_leap_year_february(self, monkeypatch):
        """Test February in leap year (2024)."""
        import pendulum

        # Mock today to be in February 2024 (leap year)
        fixed_today = pendulum.parse("2024-02-15T12:00:00")
        monkeypatch.setattr(pendulum, "today", lambda: fixed_today)

        result = get_relative_date_frame("MONTH", 0)
        assert result == ("2024-02-01", "2024-02-29")  # 29 days in leap year

    def test_non_leap_year_february(self, monkeypatch):
        """Test February in non-leap year (2023)."""
        import pendulum

        # Mock today to be in February 2023 (non-leap year)
        fixed_today = pendulum.parse("2023-02-15T12:00:00")
        monkeypatch.setattr(pendulum, "today", lambda: fixed_today)

        result = get_relative_date_frame("MONTH", 0)
        assert result == ("2023-02-01", "2023-02-28")  # 28 days in non-leap year

    # ==================== WEEK START TESTS ====================
    def test_week_starts_monday(self, mock_today):
        """Test that weeks start on Monday (ISO 8601 standard)."""
        # Our mock date is Saturday 2024-06-15
        result = get_relative_date_frame("WEEK", 0)
        start_date, end_date = result

        # Week should start on Monday 2024-06-10 and end on Sunday 2024-06-16
        assert start_date == "2024-06-10"  # Monday
        assert end_date == "2024-06-16"  # Sunday

    @pytest.mark.parametrize(
        "mock_date, expected_week_start, expected_week_end",
        [
            ("2024-06-10", "2024-06-10", "2024-06-16"),  # Monday
            ("2024-06-11", "2024-06-10", "2024-06-16"),  # Tuesday
            ("2024-06-12", "2024-06-10", "2024-06-16"),  # Wednesday
            ("2024-06-13", "2024-06-10", "2024-06-16"),  # Thursday
            ("2024-06-14", "2024-06-10", "2024-06-16"),  # Friday
            ("2024-06-15", "2024-06-10", "2024-06-16"),  # Saturday
            ("2024-06-16", "2024-06-10", "2024-06-16"),  # Sunday
        ],
    )
    def test_week_boundaries_all_days(self, monkeypatch, mock_date, expected_week_start, expected_week_end):
        """Test that same week is returned regardless of which day we start from."""
        import pendulum

        fixed_today = pendulum.parse(f"{mock_date}T12:00:00")
        monkeypatch.setattr(pendulum, "today", lambda: fixed_today)

        result = get_relative_date_frame("WEEK", 0)
        assert result == (expected_week_start, expected_week_end)

    # ==================== DEFAULT PARAMETERS ====================
    def test_default_parameters(self, mock_today):
        """Test function with default parameters (MONTH, n=0)."""
        result = get_relative_date_frame()
        expected = get_relative_date_frame("MONTH", 0)
        assert result == expected
        assert result == ("2024-06-01", "2024-06-30")

    def test_default_month_parameter(self, mock_today):
        """Test function with only n parameter (default MONTH)."""
        result = get_relative_date_frame(n=-1)
        expected = get_relative_date_frame("MONTH", -1)
        assert result == expected
        assert result == ("2024-05-01", "2024-05-31")

    # ==================== ERROR HANDLING ====================
    @pytest.mark.parametrize(
        "invalid_date_part",
        [
            "day",  # lowercase
            "DAYS",  # plural
            "months",  # plural + lowercase
            "invalid",  # completely invalid
            "SEMESTER",  # not supported
            "",  # empty string
            None,  # None value
        ],
    )
    def test_invalid_date_part(self, mock_today, invalid_date_part):
        """Test that invalid date_part raises ValueError."""
        with pytest.raises(ValueError, match="date_part must be"):
            get_relative_date_frame(invalid_date_part, 0)

    # ==================== EDGE CASES ====================
    def test_zero_offset(self, mock_today):
        """Test that n=0 returns current period for all date parts."""
        for date_part in ["DAY", "WEEK", "MONTH", "QUARTER", "YEAR"]:
            result = get_relative_date_frame(date_part, 0)
            start_date, end_date = result

            # Verify format
            assert len(start_date) == 10  # YYYY-MM-DD
            assert len(end_date) == 10  # YYYY-MM-DD
            assert start_date <= end_date  # Start should be before or equal to end

    def test_large_offsets(self, mock_today):
        """Test with large positive and negative offsets."""
        # Large positive offset
        result = get_relative_date_frame("YEAR", 100)
        assert result == ("2124-01-01", "2124-12-31")

        # Large negative offset
        result = get_relative_date_frame("YEAR", -100)
        assert result == ("1924-01-01", "1924-12-31")

    # ==================== date_from PARAMETER TESTS ====================
    def test_date_from_string(self):
        """Test with date_from as string."""
        result = get_relative_date_frame("MONTH", 0, date_from="2024-06-15")
        assert result == ("2024-06-01", "2024-06-30")

        # Test different month
        result = get_relative_date_frame("MONTH", 0, date_from="2024-02-15")
        assert result == ("2024-02-01", "2024-02-29")  # Leap year

    def test_date_from_object(self):
        """Test with date_from as date object."""
        from datetime import date

        result = get_relative_date_frame("MONTH", 0, date_from=date(2024, 6, 15))
        assert result == ("2024-06-01", "2024-06-30")

        # Test different month
        result = get_relative_date_frame("MONTH", 0, date_from=date(2024, 2, 15))
        assert result == ("2024-02-01", "2024-02-29")  # Leap year

    @pytest.mark.parametrize(
        "date_from, date_part, n, expected",
        [
            ("2024-06-15", "DAY", 0, ("2024-06-15", "2024-06-15")),
            ("2024-06-15", "DAY", 1, ("2024-06-16", "2024-06-16")),
            ("2024-06-15", "DAY", -1, ("2024-06-14", "2024-06-14")),
            ("2024-06-15", "WEEK", 0, ("2024-06-10", "2024-06-16")),  # Same week
            ("2024-06-15", "MONTH", 0, ("2024-06-01", "2024-06-30")),
            ("2024-06-15", "MONTH", 1, ("2024-07-01", "2024-07-31")),
            ("2024-06-15", "MONTH", -1, ("2024-05-01", "2024-05-31")),
            ("2024-06-15", "QUARTER", 0, ("2024-04-01", "2024-06-30")),  # Q2
            ("2024-06-15", "QUARTER", 1, ("2024-07-01", "2024-09-30")),  # Q3
            ("2024-06-15", "QUARTER", -1, ("2024-01-01", "2024-03-31")),  # Q1
            ("2024-06-15", "YEAR", 0, ("2024-01-01", "2024-12-31")),
            ("2024-06-15", "YEAR", 1, ("2025-01-01", "2025-12-31")),
            ("2024-06-15", "YEAR", -1, ("2023-01-01", "2023-12-31")),
        ],
    )
    def test_date_from_parametrized(self, date_from, date_part, n, expected):
        """Test date_from parameter with various combinations."""
        result = get_relative_date_frame(date_part, n, date_from=date_from)
        assert result == expected

    def test_date_from_vs_mock_today(self, mock_today):
        """Test that date_from overrides current date."""
        # With mock_today (2024-06-15), current month would be June
        result_mock = get_relative_date_frame("MONTH", 0)
        assert result_mock == ("2024-06-01", "2024-06-30")

        # With date_from, should get different month
        result_date_from = get_relative_date_frame("MONTH", 0, date_from="2024-12-15")
        assert result_date_from == ("2024-12-01", "2024-12-31")

        # Results should be different
        assert result_mock != result_date_from

    def test_date_from_quarter_calculations(self):
        """Test quarter calculations with different date_from values."""
        # Test from different quarters
        q1_result = get_relative_date_frame("QUARTER", 0, date_from="2024-02-15")
        assert q1_result == ("2024-01-01", "2024-03-31")  # Q1

        q2_result = get_relative_date_frame("QUARTER", 0, date_from="2024-05-15")
        assert q2_result == ("2024-04-01", "2024-06-30")  # Q2

        q3_result = get_relative_date_frame("QUARTER", 0, date_from="2024-08-15")
        assert q3_result == ("2024-07-01", "2024-09-30")  # Q3

        q4_result = get_relative_date_frame("QUARTER", 0, date_from="2024-11-15")
        assert q4_result == ("2024-10-01", "2024-12-31")  # Q4

    def test_date_from_year_boundaries(self):
        """Test year boundary calculations with date_from."""
        # Test calculations across year boundaries
        result = get_relative_date_frame("MONTH", 1, date_from="2024-12-15")
        assert result == ("2025-01-01", "2025-01-31")  # Next month in next year

        result = get_relative_date_frame("MONTH", -1, date_from="2024-01-15")
        assert result == ("2023-12-01", "2023-12-31")  # Previous month in previous year

        result = get_relative_date_frame("QUARTER", 1, date_from="2024-11-15")
        assert result == ("2025-01-01", "2025-03-31")  # Next quarter in next year

    # ==================== RETURN TYPE VERIFICATION ====================
    def test_return_type(self, mock_today):
        """Test that function returns tuple of two strings."""
        result = get_relative_date_frame("MONTH", 0)

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], str)
        assert isinstance(result[1], str)

        # Verify date format (YYYY-MM-DD)
        start_date, end_date = result
        assert len(start_date.split("-")) == 3
        assert len(end_date.split("-")) == 3


class TestDateTimeSupport:
    """Test datetime object support in existing functions."""

    def test_format_year_month_with_datetime(self):
        """Test format_year_month with datetime objects."""
        dt = datetime(2024, 3, 15, 12, 30, 45)
        result = format_year_month(dt)
        assert result == "2024-03"

    def test_generate_date_array_with_datetime(self):
        """Test generate_date_array with datetime objects."""
        start_dt = datetime(2024, 1, 1, 8, 0)
        end_dt = datetime(2024, 1, 3, 18, 30)

        result = generate_date_array(start_dt, end_dt)
        expected = [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)]
        assert result == expected

    def test_get_relative_date_frame_with_datetime(self):
        """Test get_relative_date_frame with datetime objects."""
        dt = datetime(2024, 6, 15, 14, 30)

        result = get_relative_date_frame("MONTH", 0, date_from=dt)
        expected = ("2024-06-01", "2024-06-30")
        assert result == expected

    def test_mixed_datetime_and_date_inputs(self):
        """Test mixing datetime and date objects in same function call."""
        start_dt = datetime(2024, 1, 1, 10, 0)
        end_date = date(2024, 1, 5)

        result = generate_date_array(start_dt, end_date)
        expected = [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4), date(2024, 1, 5)]
        assert result == expected


class TestDateRange:
    """Test cases for DateRange class."""

    # ==================== FIXTURES ====================
    @pytest.fixture
    def sample_date_range(self):
        """Sample DateRange for testing."""
        return DateRange("2024-01-01", "2024-01-07")

    @pytest.fixture
    def single_day_range(self):
        """Single day DateRange for testing."""
        return DateRange("2024-01-15")

    # ==================== INITIALIZATION TESTS ====================
    def test_init_no_args(self):
        """Test DateRange() creates today-today range."""
        dr = DateRange()
        today_str = date.today().isoformat()
        assert dr.date_start == today_str
        assert dr.date_end == today_str

    def test_init_single_date(self):
        """Test DateRange(date) creates single day range."""
        dr = DateRange("2024-01-15")
        assert dr.date_start == "2024-01-15"
        assert dr.date_end == "2024-01-15"

    def test_init_date_range(self):
        """Test DateRange(start, end) creates proper range."""
        dr = DateRange("2024-01-01", "2024-01-31")
        assert dr.date_start == "2024-01-01"
        assert dr.date_end == "2024-01-31"

    def test_init_with_date_objects(self):
        """Test initialization with date objects."""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)
        dr = DateRange(start_date, end_date)
        assert dr.date_start == "2024-01-01"
        assert dr.date_end == "2024-01-31"

    def test_init_with_datetime_objects(self):
        """Test initialization with datetime objects."""
        start_dt = datetime(2024, 1, 1, 10, 30)
        end_dt = datetime(2024, 1, 31, 15, 45)
        dr = DateRange(start_dt, end_dt)
        assert dr.date_start == "2024-01-01"
        assert dr.date_end == "2024-01-31"

    # ==================== STRING REPRESENTATION ====================
    def test_str_representation(self, sample_date_range):
        """Test string representation of DateRange."""
        result = str(sample_date_range)
        assert result == "[2024-01-01 → 2024-01-07]"

    # ==================== CONVERSION METHODS ====================
    def test_as_tuple(self, sample_date_range):
        """Test as_tuple method."""
        result = sample_date_range.as_tuple()
        assert result == ("2024-01-01", "2024-01-07")

    def test_as_list(self, sample_date_range):
        """Test as_list method."""
        result = sample_date_range.as_list()
        assert result == ["2024-01-01", "2024-01-07"]

    def test_as_dict(self, sample_date_range):
        """Test as_dict method."""
        result = sample_date_range.as_dict()
        expected = {"date_start": "2024-01-01", "date_end": "2024-01-07"}
        assert result == expected

    def test_format_custom_template(self, sample_date_range):
        """Test format method with custom template."""
        result = sample_date_range.format("{start} to {end}")
        assert result == "2024-01-01 to 2024-01-07"

    def test_to_dict_with_custom_keys(self, sample_date_range):
        """Test to_dict_with_custom_keys method."""
        result = sample_date_range.to_dict_with_custom_keys("from_date", "to_date")
        expected = {"from_date": "2024-01-01", "to_date": "2024-01-07"}
        assert result == expected

    def test_to_fb_time_range(self, sample_date_range):
        """Test to_fb_time_range method."""
        result = sample_date_range.to_fb_time_range()
        expected = {"since": "2024-01-01", "until": "2024-01-07"}
        assert result == expected

    # ==================== UTILITY METHODS ====================
    def test_contains_date_in_range(self, sample_date_range):
        """Test contains method with date in range."""
        assert sample_date_range.contains("2024-01-03") is True
        assert sample_date_range.contains("2024-01-01") is True  # boundary
        assert sample_date_range.contains("2024-01-07") is True  # boundary

    def test_contains_date_outside_range(self, sample_date_range):
        """Test contains method with date outside range."""
        assert sample_date_range.contains("2023-12-31") is False
        assert sample_date_range.contains("2024-01-08") is False

    def test_contains_with_date_object(self, sample_date_range):
        """Test contains method with date object."""
        test_date = date(2024, 1, 5)
        assert sample_date_range.contains(test_date) is True

    def test_overlaps_true(self):
        """Test overlaps method when ranges overlap."""
        dr1 = DateRange("2024-01-01", "2024-01-10")
        dr2 = DateRange("2024-01-05", "2024-01-15")
        assert dr1.overlaps(dr2) is True
        assert dr2.overlaps(dr1) is True

    def test_overlaps_false(self):
        """Test overlaps method when ranges don't overlap."""
        dr1 = DateRange("2024-01-01", "2024-01-10")
        dr2 = DateRange("2024-01-15", "2024-01-20")
        assert dr1.overlaps(dr2) is False
        assert dr2.overlaps(dr1) is False

    def test_overlaps_adjacent(self):
        """Test overlaps method with adjacent ranges."""
        dr1 = DateRange("2024-01-01", "2024-01-10")
        dr2 = DateRange("2024-01-11", "2024-01-20")
        assert dr1.overlaps(dr2) is False

    def test_days_count(self, sample_date_range):
        """Test days_count method."""
        result = sample_date_range.days_count()
        assert result == 7  # 2024-01-01 to 2024-01-07 inclusive

    def test_days_count_single_day(self, single_day_range):
        """Test days_count method for single day."""
        result = single_day_range.days_count()
        assert result == 1

    # ==================== MANIPULATION METHODS ====================
    def test_extend_by_days(self, sample_date_range):
        """Test extend_by_days method."""
        result = sample_date_range.extend_by_days(2, 3)
        assert result.date_start == "2023-12-30"  # 2 days back
        assert result.date_end == "2024-01-10"  # 3 days forward

    def test_shift_by_days_forward(self, sample_date_range):
        """Test shift_by_days method forward."""
        result = sample_date_range.shift_by_days(5)
        assert result.date_start == "2024-01-06"
        assert result.date_end == "2024-01-12"

    def test_shift_by_days_backward(self, sample_date_range):
        """Test shift_by_days method backward."""
        result = sample_date_range.shift_by_days(-3)
        assert result.date_start == "2023-12-29"
        assert result.date_end == "2024-01-04"

    def test_extend_to_week_bounds(self):
        """Test extend_to_week_bounds method."""
        # Wednesday to Friday
        dr = DateRange("2024-01-03", "2024-01-05")
        result = dr.extend_to_week_bounds()
        assert result.date_start == "2024-01-01"  # Monday
        assert result.date_end == "2024-01-07"  # Sunday

    def test_extend_to_month_bounds(self):
        """Test extend_to_month_bounds method."""
        dr = DateRange("2024-01-15", "2024-02-20")
        result = dr.extend_to_month_bounds()
        assert result.date_start == "2024-01-01"  # First of January
        assert result.date_end == "2024-02-29"  # Last of February (leap year)

    # ==================== SPLITTING METHODS ====================
    def test_split_into_chunks(self, sample_date_range):
        """Test split method."""
        chunks = sample_date_range.split(3)
        assert len(chunks) == 3
        assert str(chunks[0]) == "[2024-01-01 → 2024-01-03]"
        assert str(chunks[1]) == "[2024-01-04 → 2024-01-06]"
        assert str(chunks[2]) == "[2024-01-07 → 2024-01-07]"

    def test_split_invalid_chunk_size(self, sample_date_range):
        """Test split method with invalid chunk size."""
        with pytest.raises(ValueError, match="chunk_days must be >= 1"):
            sample_date_range.split(0)

    # ==================== STATIC METHODS ====================
    def test_around_date_lookback_only(self):
        """Test around_date with only lookback."""
        dr = DateRange.around_date(date_anchor="2024-01-15", days_lookback=5)
        assert dr.date_start == "2024-01-10"
        assert dr.date_end == "2024-01-15"

    def test_around_date_lookforward_only(self):
        """Test around_date with only lookforward."""
        dr = DateRange.around_date(date_anchor="2024-01-15", days_lookforward=3)
        assert dr.date_start == "2024-01-15"
        assert dr.date_end == "2024-01-18"

    def test_around_date_both_directions(self):
        """Test around_date with both lookback and lookforward."""
        dr = DateRange.around_date(date_anchor="2024-01-15", days_lookback=2, days_lookforward=3)
        assert dr.date_start == "2024-01-13"
        assert dr.date_end == "2024-01-18"

    def test_around_date_negative_values(self):
        """Test around_date with negative values raises error."""
        with pytest.raises(ValueError, match="days_lookback/days_lookforward must be >= 0"):
            DateRange.around_date(days_lookback=-1)

    def test_single_calendar_period_current_month(self):
        """Test single_calendar_period for current month."""
        dr = DateRange.single_calendar_period("MONTH", offset=0, date_anchor="2024-06-15")
        assert dr.date_start == "2024-06-01"
        assert dr.date_end == "2024-06-30"

    def test_single_calendar_period_previous_week(self):
        """Test single_calendar_period for previous week."""
        dr = DateRange.single_calendar_period(
            "WEEK",
            offset=-1,
            date_anchor="2024-06-15",  # Saturday
        )
        # Previous week should be June 3-9, 2024
        assert dr.date_start == "2024-06-03"
        assert dr.date_end == "2024-06-09"

    # ==================== TIMESTAMP METHODS ====================
    def test_to_timestamps_utc(self):
        """Test to_timestamps method with UTC."""
        dr = DateRange("2024-01-01", "2024-01-02")
        result = dr.to_timestamps()

        assert "starts_at" in result
        assert "ends_at" in result
        assert result["starts_at"] == "2024-01-01T00:00:00Z"
        assert result["ends_at"] == "2024-01-03T00:00:00Z"  # +1 day

    def test_to_timestamps_with_timezone(self):
        """Test to_timestamps method with timezone."""
        dr = DateRange("2024-01-01", "2024-01-01")
        result = dr.to_timestamps(tz="Europe/London")

        assert "starts_at" in result
        assert "ends_at" in result
        # London time should be converted to UTC
        assert result["starts_at"] == "2024-01-01T00:00:00Z"
        assert result["ends_at"] == "2024-01-02T00:00:00Z"

    def test_to_reddit_range(self):
        """Test to_reddit_range method."""
        dr = DateRange("2024-01-01", "2024-01-01")
        result = dr.to_reddit_range()

        assert "starts_at" in result
        assert "ends_at" in result
        assert result["starts_at"] == "2024-01-01T00:00:00Z"
        assert result["ends_at"] == "2024-01-02T00:00:00Z"


class TestDateRanges:
    """Test cases for DateRanges class."""

    @pytest.fixture
    def date_ranges_generator(self):
        """DateRanges instance for testing."""
        return DateRanges()

    # ==================== CALENDAR PERIODS ====================
    def test_calendar_periods_weeks(self, date_ranges_generator):
        """Test calendar_periods with weeks."""
        ranges = date_ranges_generator.calendar_periods(
            "WEEK",
            count=2,
            date_end="2024-01-14",  # Sunday
        )

        assert len(ranges) == 2
        # Most recent week first
        assert ranges[0].date_start == "2024-01-08"  # Monday
        assert ranges[0].date_end == "2024-01-14"  # Sunday
        assert ranges[1].date_start == "2024-01-01"  # Previous Monday
        assert ranges[1].date_end == "2024-01-07"  # Previous Sunday

    def test_calendar_periods_months(self, date_ranges_generator):
        """Test calendar_periods with months."""
        ranges = date_ranges_generator.calendar_periods("MONTH", count=2, date_end="2024-02-15")

        assert len(ranges) == 2
        # Current month (February)
        assert ranges[0].date_start == "2024-02-01"
        assert ranges[0].date_end == "2024-02-15"  # Trimmed to date_end
        # Previous month (January)
        assert ranges[1].date_start == "2024-01-01"
        assert ranges[1].date_end == "2024-01-31"

    def test_calendar_periods_no_trim(self, date_ranges_generator):
        """Test calendar_periods without trimming."""
        ranges = date_ranges_generator.calendar_periods("MONTH", count=1, date_end="2024-02-15", trim_last_period=False)

        assert len(ranges) == 1
        assert ranges[0].date_start == "2024-02-01"
        assert ranges[0].date_end == "2024-02-29"  # Full month, not trimmed

    # ==================== OFFSET RANGE BUCKETS ====================
    def test_offset_range_buckets(self, date_ranges_generator):
        """Test offset_range_buckets method."""
        ranges = date_ranges_generator.offset_range_buckets(
            "WEEK", offset_start=0, offset_end=-2, date_end="2024-01-14"
        )

        assert len(ranges) == 3  # 0, -1, -2
        # Current week (offset 0)
        assert ranges[0].date_start == "2024-01-08"
        assert ranges[0].date_end == "2024-01-14"

    # ==================== SPLIT LOOKBACK PERIOD ====================
    def test_split_lookback_period(self, date_ranges_generator):
        """Test split_lookback_period method."""
        ranges = date_ranges_generator.split_lookback_period(total_days=10, chunk_days=3, date_end="2024-01-10")

        # Should create chunks working backwards from end date
        assert len(ranges) == 4  # 3+3+3+1 days
        # Most recent chunk first
        assert ranges[0].date_start == "2024-01-08"
        assert ranges[0].date_end == "2024-01-10"

    def test_split_lookback_period_invalid_chunk_size(self, date_ranges_generator):
        """Test split_lookback_period with invalid chunk size."""
        with pytest.raises(ValueError, match="chunk_days must be >= 1"):
            date_ranges_generator.split_lookback_period(total_days=10, chunk_days=0)


# ==================== COVERAGE TESTS FOR UNCOVERED LINES ====================
class TestUncoveredLines:
    """Tests specifically targeting previously uncovered code paths."""

    def test_december_month_boundary_extend_to_month_bounds(self):
        """Test line 582: December month end calculation in extend_to_month_bounds."""
        # Create range that ends in December to trigger year rollover logic
        dr = DateRange("2024-12-15", "2024-12-31")
        extended = dr.extend_to_month_bounds()

        # Should extend to full December month
        assert extended.date_start == "2024-12-01"
        assert extended.date_end == "2024-12-31"

        # Test with range spanning into December
        dr_span = DateRange("2024-11-15", "2024-12-15")
        extended_span = dr_span.extend_to_month_bounds()

        # Should span November to December
        assert extended_span.date_start == "2024-11-01"
        assert extended_span.date_end == "2024-12-31"

    def test_offset_range_buckets_date_trimming(self):
        """Test line 735: date trimming in offset_range_buckets."""
        generator = DateRanges()

        # Create scenario where period end exceeds date_end to force trimming
        ranges = generator.offset_range_buckets(
            "WEEK",
            offset_start=0,
            offset_end=-2,
            date_end="2024-01-03",  # Mid-week date to force trimming
        )

        # Current week should be trimmed to date_end
        assert len(ranges) == 3  # 0, -1, -2 offsets

        # First range (current week) should be trimmed
        current_week = ranges[0]
        assert current_week.date_end == "2024-01-03"  # Trimmed to date_end

        # Previous weeks should not be affected by trimming
        prev_week = ranges[1]
        assert prev_week.date_end != "2024-01-03"  # Not trimmed


# ==================== PERFORMANCE AND STRESS TESTS ====================
class TestPerformance:
    """Performance and stress tests for date utilities."""

    def test_date_utilities_performance_large_dataset(self):
        """Test performance with large datasets."""
        import time

        # Create large mixed dataset
        dates = []
        for i in range(1000):
            dates.extend(
                [
                    f"2024-{(i % 12) + 1:02d}-15",
                    datetime(2024, (i % 12) + 1, 15, 12, 30),
                    date(2024, (i % 12) + 1, 15),
                ]
            )

        # Test to_date performance
        start = time.time()
        results_to_date = [to_date(d) for d in dates]
        to_date_duration = time.time() - start

        # Test to_date_iso_str performance
        start = time.time()
        results_to_iso = [to_date_iso_str(d) for d in dates]
        to_iso_duration = time.time() - start

        # Should complete reasonably fast
        assert to_date_duration < 1.0  # Less than 1 second
        assert to_iso_duration < 1.0  # Less than 1 second

        # Results should be correct length
        assert len(results_to_date) == len(dates)
        assert len(results_to_iso) == len(dates)

        # All results should be proper types
        assert all(isinstance(d, date) for d in results_to_date)
        assert all(isinstance(s, str) for s in results_to_iso)

    def test_date_range_splitting_performance(self):
        """Test performance of date range splitting with large ranges."""
        import time

        # Create large date range (1 year)
        dr = DateRange("2024-01-01", "2024-12-31")

        start = time.time()
        chunks = dr.split(7)  # Weekly chunks for whole year
        duration = time.time() - start

        # Should complete quickly
        assert duration < 0.1  # Less than 100ms

        # Should have correct number of chunks (52+ weeks)
        assert len(chunks) >= 52
        assert len(chunks) <= 54  # Account for partial weeks

        # All chunks should be valid DateRange objects
        assert all(isinstance(chunk, DateRange) for chunk in chunks)


# ==================== INTEGRATION TESTS ====================
class TestRealWorldScenarios:
    """Integration tests with realistic ETL scenarios."""

    def test_mixed_api_data_processing(self):
        """Test processing mixed date formats from APIs."""
        # Simulate real API data with mixed date formats
        api_data = [
            {"id": 1, "created_at": "2024-01-15T10:30:00Z", "event": "login"},
            {"id": 2, "created_at": datetime(2024, 1, 16, 14, 20), "event": "purchase"},
            {"id": 3, "created_at": date(2024, 1, 17), "event": "logout"},
            {"id": 4, "created_at": "2024-01-18", "event": "signup"},
        ]

        # Normalize all dates to ISO strings
        normalized = []
        for item in api_data:
            item_copy = item.copy()
            item_copy["date"] = to_date_iso_str(item["created_at"])
            item_copy["date_obj"] = to_date(item["created_at"])
            normalized.append(item_copy)

        # All should have consistent date format
        expected_dates = ["2024-01-15", "2024-01-16", "2024-01-17", "2024-01-18"]
        actual_dates = [item["date"] for item in normalized]
        assert actual_dates == expected_dates

        # All date objects should be proper date type
        date_objects = [item["date_obj"] for item in normalized]
        assert all(isinstance(d, date) for d in date_objects)
        assert all(not isinstance(d, datetime) for d in date_objects)

    def test_date_range_etl_workflow(self):
        """Test complete ETL workflow using DateRange utilities."""
        # Simulate ETL scenario: process data in weekly chunks
        generator = DateRanges()

        # Get last 4 weeks of data
        weeks = generator.calendar_periods("WEEK", count=4, date_end="2024-01-28")

        # Process each week
        processed_weeks = []
        for week in weeks:
            # Convert to different formats for different systems
            week_data = {
                "range_str": str(week),
                "tuple": week.as_tuple(),
                "fb_format": week.to_fb_time_range(),
                "timestamps": week.to_timestamps(),
                "days_count": week.days_count(),
            }
            processed_weeks.append(week_data)

        # Should have 4 weeks
        assert len(processed_weeks) == 4

        # Each week should have all required formats
        for week_data in processed_weeks:
            assert "range_str" in week_data
            assert "tuple" in week_data
            assert "fb_format" in week_data
            assert "timestamps" in week_data
            assert "days_count" in week_data

            # Days count should be 7 for complete weeks
            assert week_data["days_count"] == 7
