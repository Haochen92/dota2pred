import pytest
from datetime import datetime, timezone, timedelta
from dota_oracle_common.utils.time_utils import to_utc_datetime_object
from typing import Any


def test_to_utc_aware_datetime() -> None:
    dt_input = datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    expected_dt = dt_input  # Should remain unchanged
    assert to_utc_datetime_object(dt_input) == expected_dt


def test_to_utc_naive_datetime() -> None:
    dt_input = datetime(2023, 1, 1, 10, 0, 0)
    expected_dt = datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    assert to_utc_datetime_object(dt_input) == expected_dt


def test_to_utc_different_timezone_datetime() -> None:
    # Example: EST is UTC-5
    est = timezone(timedelta(hours=-5))
    dt_input = datetime(2023, 1, 1, 5, 0, 0, tzinfo=est)  # 5 AM EST
    expected_dt = datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)  # 10 AM UTC
    assert to_utc_datetime_object(dt_input) == expected_dt


# Test with Unix timestamp (seconds)
def test_to_utc_unix_timestamp_seconds() -> None:
    # 01/01/2023 10:00:00 UTC
    timestamp_input = 1672567200
    expected_dt = datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    assert to_utc_datetime_object(timestamp_input) == expected_dt


# Test with a custom format string (naive, assumed UTC)
@pytest.mark.parametrize(
    "str_input, fmt_in_code",
    [
        ("2023-01-01 10:00:00", "%Y-%m-%d %H:%M:%S"),
        ("2023-01-01 10:00:00.123456", "%Y-%m-%d %H:%M:%S.%f"),
        ("2023/01/01 10:00:00", "%Y/%m/%d %H:%M:%S"),
        ("01-01-2023 10:00:00", "%d-%m-%Y %H:%M:%S"),
    ],
)
def test_to_utc_custom_format_string(str_input: str, fmt_in_code: str) -> None:
    # This test assumes the custom format parsing results in a naive datetime
    # which is then made UTC aware.
    dt_naive_expected = datetime.strptime(str_input, fmt_in_code)
    expected_dt = dt_naive_expected.replace(tzinfo=timezone.utc)
    assert to_utc_datetime_object(str_input) == expected_dt


# Test for unsupported input type
def test_to_utc_unsupported_type_raises_type_error() -> None:
    list_input = [2023, 1, 1]
    with pytest.raises(TypeError, match="Unsupported input type for time conversion"):
        to_utc_datetime_object(list_input)


def test_to_utc_internal_conversion_failure_raise_value_error(mocker: Any) -> None:
    empty_string_input = ""
    with pytest.raises(ValueError, match=f"String '{empty_string_input}' could not be parsed"):
        to_utc_datetime_object(empty_string_input)
