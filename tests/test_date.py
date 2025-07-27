from datetime import date

import pytest

from etlutil.date import format_year_month, generate_date_array


class TestGenerateDateArray:
    """Test cases for generate_date_array function."""

    def test_basic_date_range(self):
        """Test basic date range with default parameters."""
        result = generate_date_array("2024-01-01", "2024-01-05")
        expected = [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4), date(2024, 1, 5)]
        assert result == expected

    def test_date_objects_input(self):
        """Test with date objects instead of strings."""
        result = generate_date_array(date(2024, 1, 1), date(2024, 1, 3))
        expected = [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)]
        assert result == expected

    def test_mixed_input_types(self):
        """Test with mixed input types (string and date object)."""
        result = generate_date_array("2024-01-01", date(2024, 1, 3))
        expected = [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)]
        assert result == expected

    def test_interval_days(self):
        """Test with custom day interval."""
        result = generate_date_array("2024-01-01", "2024-01-10", 2, "DAY")
        expected = [date(2024, 1, 1), date(2024, 1, 3), date(2024, 1, 5), date(2024, 1, 7), date(2024, 1, 9)]
        assert result == expected

    def test_interval_weeks(self):
        """Test with week interval."""
        result = generate_date_array("2024-01-01", "2024-01-22", 1, "WEEK")
        expected = [date(2024, 1, 1), date(2024, 1, 8), date(2024, 1, 15), date(2024, 1, 22)]
        assert result == expected

    def test_interval_months(self):
        """Test with month interval."""
        result = generate_date_array("2024-01-01", "2024-06-01", 1, "MONTH")
        expected = [
            date(2024, 1, 1),
            date(2024, 2, 1),
            date(2024, 3, 1),
            date(2024, 4, 1),
            date(2024, 5, 1),
            date(2024, 6, 1),
        ]
        assert result == expected

    def test_interval_quarters(self):
        """Test with quarter interval."""
        result = generate_date_array("2024-01-01", "2024-12-01", 1, "QUARTER")
        expected = [date(2024, 1, 1), date(2024, 4, 1), date(2024, 7, 1), date(2024, 10, 1)]
        assert result == expected

    def test_interval_years(self):
        """Test with year interval."""
        result = generate_date_array("2024-01-01", "2028-01-01", 1, "YEAR")
        expected = [date(2024, 1, 1), date(2025, 1, 1), date(2026, 1, 1), date(2027, 1, 1), date(2028, 1, 1)]
        assert result == expected

    def test_custom_interval_months(self):
        """Test with custom month interval."""
        result = generate_date_array("2024-01-01", "2024-07-01", 2, "MONTH")
        expected = [date(2024, 1, 1), date(2024, 3, 1), date(2024, 5, 1), date(2024, 7, 1)]
        assert result == expected

    def test_empty_range(self):
        """Test when start date is after end date."""
        result = generate_date_array("2024-01-05", "2024-01-01")
        assert result == []

    def test_single_date(self):
        """Test when start and end dates are the same."""
        result = generate_date_array("2024-01-01", "2024-01-01")
        expected = [date(2024, 1, 1)]
        assert result == expected

    def test_zero_interval_returns_empty(self):
        """Test that zero interval returns empty list."""
        result = generate_date_array("2024-01-01", "2024-01-05", 0)
        assert result == []

    def test_invalid_date_format(self):
        """Test that invalid date format raises ValueError."""
        with pytest.raises(ValueError):
            generate_date_array("invalid-date", "2024-01-05")

    def test_leap_year_handling(self):
        """Test handling of leap years."""
        result = generate_date_array("2024-02-28", "2024-03-01")
        expected = [
            date(2024, 2, 28),
            date(2024, 2, 29),  # Leap day
            date(2024, 3, 1),
        ]
        assert result == expected

    def test_month_end_handling(self):
        """Test handling of month end dates."""
        result = generate_date_array("2024-01-31", "2024-03-31", 1, "MONTH")
        expected = [
            date(2024, 1, 31),
            date(2024, 2, 29),  # February 29 in leap year
            date(2024, 3, 31),
        ]
        assert result == expected

    def test_large_interval(self):
        """Test with large interval values."""
        result = generate_date_array("2024-01-01", "2024-12-31", 30, "DAY")
        expected = [
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
        ]
        assert result == expected

    def test_negative_interval_days(self):
        """Test with negative day interval."""
        result = generate_date_array("2024-01-05", "2024-01-01", -1, "DAY")
        expected = [date(2024, 1, 5), date(2024, 1, 4), date(2024, 1, 3), date(2024, 1, 2), date(2024, 1, 1)]
        assert result == expected

    def test_negative_interval_weeks(self):
        """Test with negative week interval."""
        result = generate_date_array("2024-01-22", "2024-01-01", -1, "WEEK")
        expected = [date(2024, 1, 22), date(2024, 1, 15), date(2024, 1, 8), date(2024, 1, 1)]
        assert result == expected

    def test_negative_interval_months(self):
        """Test with negative month interval."""
        result = generate_date_array("2024-06-01", "2024-01-01", -1, "MONTH")
        expected = [
            date(2024, 6, 1),
            date(2024, 5, 1),
            date(2024, 4, 1),
            date(2024, 3, 1),
            date(2024, 2, 1),
            date(2024, 1, 1),
        ]
        assert result == expected

    def test_negative_interval_quarters(self):
        """Test with negative quarter interval."""
        result = generate_date_array("2024-12-01", "2024-01-01", -1, "QUARTER")
        expected = [date(2024, 12, 1), date(2024, 9, 1), date(2024, 6, 1), date(2024, 3, 1)]
        assert result == expected

    def test_negative_interval_years(self):
        """Test with negative year interval."""
        result = generate_date_array("2028-01-01", "2024-01-01", -1, "YEAR")
        expected = [date(2028, 1, 1), date(2027, 1, 1), date(2026, 1, 1), date(2025, 1, 1), date(2024, 1, 1)]
        assert result == expected

    def test_negative_interval_custom_days(self):
        """Test with custom negative day interval."""
        result = generate_date_array("2024-01-10", "2024-01-01", -2, "DAY")
        expected = [date(2024, 1, 10), date(2024, 1, 8), date(2024, 1, 6), date(2024, 1, 4), date(2024, 1, 2)]
        assert result == expected

    def test_negative_interval_custom_months(self):
        """Test with custom negative month interval."""
        result = generate_date_array("2024-12-01", "2024-01-01", -2, "MONTH")
        expected = [
            date(2024, 12, 1),
            date(2024, 10, 1),
            date(2024, 8, 1),
            date(2024, 6, 1),
            date(2024, 4, 1),
            date(2024, 2, 1),
        ]
        assert result == expected

    def test_negative_interval_edge_cases(self):
        """Test negative interval edge cases."""
        # Same start and end date with negative interval
        result = generate_date_array("2024-01-01", "2024-01-01", -1, "DAY")
        expected = [date(2024, 1, 1)]
        assert result == expected

        # Start date before end date with negative interval
        result = generate_date_array("2024-01-01", "2024-01-05", -1, "DAY")
        assert result == []


class TestFormatYearMonth:
    """Test cases for format_year_month function."""

    def test_basic_date_object(self):
        """Test with date object."""
        result = format_year_month(date(2024, 3, 16))
        assert result == "2024-03"

    def test_date_string_input(self):
        """Test with date string."""
        result = format_year_month("2024-03-16")
        assert result == "2024-03"

    def test_single_digit_month(self):
        """Test with single digit month (should add leading zero)."""
        result = format_year_month(date(2024, 1, 15))
        assert result == "2024-01"

    def test_double_digit_month(self):
        """Test with double digit month."""
        result = format_year_month(date(2024, 12, 31))
        assert result == "2024-12"

    def test_different_years(self):
        """Test with different years."""
        result = format_year_month(date(2023, 6, 10))
        assert result == "2023-06"

        result = format_year_month(date(2025, 11, 25))
        assert result == "2025-11"

    def test_edge_cases_days(self):
        """Test edge cases with different days of month."""
        # First day of month
        result = format_year_month(date(2024, 5, 1))
        assert result == "2024-05"

        # Last day of month
        result = format_year_month(date(2024, 2, 29))  # Leap year
        assert result == "2024-02"

        # Middle of month
        result = format_year_month(date(2024, 8, 15))
        assert result == "2024-08"

    def test_leap_year_february(self):
        """Test February in leap year."""
        result = format_year_month(date(2024, 2, 29))
        assert result == "2024-02"

    def test_non_leap_year_february(self):
        """Test February in non-leap year."""
        result = format_year_month(date(2023, 2, 28))
        assert result == "2023-02"

    def test_string_edge_cases(self):
        """Test string input edge cases."""
        # First day of month
        result = format_year_month("2024-05-01")
        assert result == "2024-05"

        # Last day of month
        result = format_year_month("2024-12-31")
        assert result == "2024-12"

        # Leap year February
        result = format_year_month("2024-02-29")
        assert result == "2024-02"

    def test_invalid_date_string(self):
        """Test that invalid date string raises ValueError."""
        with pytest.raises(ValueError):
            format_year_month("invalid-date")

        with pytest.raises(ValueError):
            format_year_month("2024-13-01")  # Invalid month

        with pytest.raises(ValueError):
            format_year_month("2024-02-30")  # Invalid day for February
