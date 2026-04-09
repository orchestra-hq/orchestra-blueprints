"""Unit tests for utils.py module."""

import pytest
from claude_agent.utils import calculate_average, get_user_name


class TestCalculateAverage:
    """Tests for calculate_average function."""

    def test_calculate_average_with_valid_numbers(self):
        """Test average calculation with a list of valid numbers."""
        assert calculate_average([1, 2, 3, 4, 5]) == 3.0

    def test_calculate_average_with_floats(self):
        """Test average calculation with float values."""
        assert calculate_average([1.5, 2.5, 3.0]) == pytest.approx(2.333, rel=0.01)

    def test_calculate_average_with_empty_list(self):
        """Test that empty list returns 0.0."""
        assert calculate_average([]) == 0.0

    def test_calculate_average_with_mixed_valid_and_invalid(self):
        """Test average skips non-numeric values but divides by total count."""
        # Note: function divides by len(numbers), not len(numeric_values)
        result = calculate_average([1, "invalid", 3, None, 5])
        # sum = 1 + 3 + 5 = 9, len = 5, avg = 9/5 = 1.8
        assert result == pytest.approx(1.8)

    def test_calculate_average_single_value(self):
        """Test average with a single numeric value."""
        assert calculate_average([42]) == 42.0

    def test_calculate_average_with_negative_numbers(self):
        """Test average with negative numbers."""
        assert calculate_average([-5, -3, 2]) == pytest.approx(-2.0)


class TestGetUserName:
    """Tests for get_user_name function."""

    def test_get_user_name_with_valid_user(self):
        """Test extracting and uppercasing a valid user name."""
        user = {"name": "alice", "email": "alice@example.com"}
        assert get_user_name(user) == "ALICE"

    def test_get_user_name_with_uppercase_input(self):
        """Test that name is returned in uppercase even if already uppercase."""
        user = {"name": "BOB"}
        assert get_user_name(user) == "BOB"

    def test_get_user_name_with_mixed_case(self):
        """Test uppercase conversion for mixed case names."""
        user = {"name": "ChArLiE"}
        assert get_user_name(user) == "CHARLIE"

    def test_get_user_name_missing_name_key(self):
        """Test that None is returned when 'name' key is missing."""
        user = {"email": "user@example.com"}
        assert get_user_name(user) is None

    def test_get_user_name_with_none_value(self):
        """Test that None is returned when 'name' key has None value."""
        user = {"name": None}
        assert get_user_name(user) is None

    def test_get_user_name_with_non_dict_input(self):
        """Test that None is returned for non-dictionary input."""
        assert get_user_name("not a dict") is None
        assert get_user_name(None) is None
        assert get_user_name(123) is None

    def test_get_user_name_with_non_string_name_value(self):
        """Test that None is returned when name value is not a string."""
        user = {"name": 123}
        assert get_user_name(user) is None
        user = {"name": ["list"]}
        assert get_user_name(user) is None

    def test_get_user_name_with_empty_string(self):
        """Test that empty string is still returned as uppercase."""
        user = {"name": ""}
        assert get_user_name(user) == ""
