from datetime import date

import pytest

from etlutil.date import format_year_month, generate_date_array


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
            ("2024-01-01", "2024-01-10", 2, "DAY", [date(2024, 1, 1), date(2024, 1, 3), date(2024, 1, 5), date(2024, 1, 7), date(2024, 1, 9)]),
            ("2024-01-01", "2024-01-22", 1, "WEEK", [date(2024, 1, 1), date(2024, 1, 8), date(2024, 1, 15), date(2024, 1, 22)]),
            ("2024-01-01", "2024-06-01", 1, "MONTH", [date(2024, 1, 1), date(2024, 2, 1), date(2024, 3, 1), date(2024, 4, 1), date(2024, 5, 1), date(2024, 6, 1)]),
            ("2024-01-01", "2024-12-01", 1, "QUARTER", [date(2024, 1, 1), date(2024, 4, 1), date(2024, 7, 1), date(2024, 10, 1)]),
            ("2024-01-01", "2024-07-01", 2, "MONTH", [date(2024, 1, 1), date(2024, 3, 1), date(2024, 5, 1), date(2024, 7, 1)]),
        ]
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
        ]
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
            ("2024-01-01", "2024-12-31", 30, "DAY", [
                date(2024, 1, 1), date(2024, 1, 31), date(2024, 3, 1), date(2024, 3, 31),
                date(2024, 4, 30), date(2024, 5, 30), date(2024, 6, 29), date(2024, 7, 29),
                date(2024, 8, 28), date(2024, 9, 27), date(2024, 10, 27), date(2024, 11, 26), date(2024, 12, 26)
            ]),
        ]
    )
    def test_large_interval(self, start_date, end_date, interval, interval_type, expected):
        """Test with large interval values."""
        result = generate_date_array(start_date, end_date, interval, interval_type)
        assert result == expected

    # ==================== NEGATIVE INTERVALS ====================
    @pytest.mark.parametrize(
        "start_date, end_date, interval, interval_type, expected",
        [
            ("2024-01-05", "2024-01-01", -1, "DAY", [date(2024, 1, 5), date(2024, 1, 4), date(2024, 1, 3), date(2024, 1, 2), date(2024, 1, 1)]),
            ("2024-01-22", "2024-01-01", -1, "WEEK", [date(2024, 1, 22), date(2024, 1, 15), date(2024, 1, 8), date(2024, 1, 1)]),
            ("2024-06-01", "2024-01-01", -1, "MONTH", [date(2024, 6, 1), date(2024, 5, 1), date(2024, 4, 1), date(2024, 3, 1), date(2024, 2, 1), date(2024, 1, 1)]),
            ("2024-12-01", "2024-01-01", -1, "QUARTER", [date(2024, 12, 1), date(2024, 9, 1), date(2024, 6, 1), date(2024, 3, 1)]),
            ("2028-01-01", "2024-01-01", -1, "YEAR", [date(2028, 1, 1), date(2027, 1, 1), date(2026, 1, 1), date(2025, 1, 1), date(2024, 1, 1)]),
            ("2024-01-10", "2024-01-01", -2, "DAY", [date(2024, 1, 10), date(2024, 1, 8), date(2024, 1, 6), date(2024, 1, 4), date(2024, 1, 2)]),
            ("2024-12-01", "2024-01-01", -2, "MONTH", [date(2024, 12, 1), date(2024, 10, 1), date(2024, 8, 1), date(2024, 6, 1), date(2024, 4, 1), date(2024, 2, 1)]),
        ]
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
        ]
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
        ]
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
        ]
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
        ]
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
        ]
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
        ]
    )
    def test_invalid_date_string(self, invalid_date):
        """Test that invalid date string raises ValueError."""
        with pytest.raises(ValueError):
            format_year_month(invalid_date)
