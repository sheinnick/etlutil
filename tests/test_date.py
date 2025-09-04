from datetime import date

import pytest

from etlutil.date import format_year_month, generate_date_array, get_relative_date_frame


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
