from datetime import datetime, timezone
from typing import Any


def get_current_utc_iso_timestamp() -> datetime:
    """Returns the current time in ISO 8601 format with 'Z' for UTC."""
    return datetime.now(timezone.utc)


def to_utc_datetime_object(time_input: Any) -> datetime:
    """
    Converts various time inputs (datetime objects, Unix timestamps,
    parsable date strings) to a timezone-aware datetime object in UTC.

    Handles:
    - Naive datetime objects (assumes UTC or converts from local based on policy)
    - Aware datetime objects (converts to UTC)
    - Unix timestamps (seconds or milliseconds since epoch)
    - Strings that datetime.fromisoformat() can parse
    - Strings in a list of known custom formats (e.g., '%Y-%m-%d %H:%M:%S')

    Returns:
        datetime: A timezone-aware datetime object in UTC.

    Raises:
        ValueError: If the input cannot be reliably converted.
        TypeError: If the input type is completely unexpected.
    """
    dt_object_utc = None

    if isinstance(time_input, datetime):
        if time_input.tzinfo is None or time_input.tzinfo.utcoffset(time_input) is None:
            dt_object_utc = time_input.replace(tzinfo=timezone.utc)
        else:
            dt_object_utc = time_input.astimezone(timezone.utc)

    elif isinstance(time_input, (int, float)):
        if time_input < 3_000_000_000:
            dt_object_utc = datetime.fromtimestamp(time_input, tz=timezone.utc)
        else:
            dt_object_utc = datetime.fromtimestamp(time_input / 1000.0, tz=timezone.utc)

    elif isinstance(time_input, str):
        try:
            dt_object = datetime.fromisoformat(time_input.replace("Z", "+00:00"))
            if dt_object.tzinfo is None or dt_object.tzinfo.utcoffset(dt_object) is None:
                dt_object_utc = dt_object.replace(tzinfo=timezone.utc)
            else:
                dt_object_utc = dt_object.astimezone(timezone.utc)
        except ValueError:
            custom_formats_to_try = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M:%S.%f",
                "%Y/%m/%d %H:%M:%S",
                "%d-%m-%Y %H:%M:%S",
            ]
            parsed_successfully = False
            for fmt in custom_formats_to_try:
                try:
                    dt_naive = datetime.strptime(time_input, fmt)
                    dt_object_utc = dt_naive.replace(tzinfo=timezone.utc)
                    parsed_successfully = True
                    break
                except ValueError:
                    continue
            if not parsed_successfully:
                raise ValueError(f"String '{time_input}' could not be parsed as ISO 8601 or any known custom format.")
    else:
        raise TypeError(f"Unsupported input type for time conversion: {type(time_input)}")

    if dt_object_utc is None:
        raise ValueError(f"Could not convert input '{time_input}' to a UTC datetime object.")

    return dt_object_utc
