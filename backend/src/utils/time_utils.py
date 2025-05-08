from datetime import datetime, timezone

def get_current_utc_iso_timestamp() -> str:
    """Returns the current time in ISO 8601 format with 'Z' for UTC."""
    return datetime.now(timezone.utc).isoformat()


# Helper function to parse all time formats to the standardized ISO 8601 format
def to_utc_iso_string(time_input: any) -> str:
    """
    Converts various time inputs (datetime objects, Unix timestamps,
    parsable date strings) to an ISO 8601 UTC string.

    Handles:
    - Naive datetime objects (assumes UTC or converts from local based on policy)
    - Aware datetime objects (converts to UTC)
    - Unix timestamps (seconds or milliseconds since epoch)
    - Strings that datetime.fromisoformat() can parse
    - Strings in a list of known custom formats (e.g., '%Y-%m-%d %H:%M:%S')

    Returns:
        str: The time in ISO 8601 UTC format (e.g., "2023-10-28T12:34:56.789012Z").
             Uses '+00:00' if 'Z' replacement is not explicitly done.
    
    Raises:
        ValueError: If the input cannot be reliably converted.
        TypeError: If the input type is completely unexpected.
    """
    dt_object_utc = None

    if isinstance(time_input, datetime):
        if time_input.tzinfo is None or time_input.tzinfo.utcoffset(time_input) is None:
            # Policy for NAIVE datetime: Assume it's UTC.
            # Alternative: Assume local time: dt_object_utc = time_input.astimezone(timezone.utc)
            # Be very careful with assuming local time if the server might run in different timezones.
            # Explicitly making it UTC is often safer if the source of naive datetimes is known.
            dt_object_utc = time_input.replace(tzinfo=timezone.utc)
        else:
            # It's an AWARE datetime, convert to UTC
            dt_object_utc = time_input.astimezone(timezone.utc)

    elif isinstance(time_input, (int, float)):
        # Assume Unix timestamp (seconds or milliseconds)
        # A common heuristic: if the number is very large (e.g., > 3e9 for seconds, >3e12 for ms),
        # it's likely milliseconds.
        # This is not foolproof; context is better.
        # For simplicity, let's assume if it's < 3_000_000_000 it's seconds, else milliseconds
        # (This covers dates roughly up to year 2065 for seconds)
        if time_input < 3_000_000_000: # Likely seconds
            dt_object_utc = datetime.fromtimestamp(time_input, tz=timezone.utc)
        else: # Likely milliseconds
            dt_object_utc = datetime.fromtimestamp(time_input / 1000.0, tz=timezone.utc)

    elif isinstance(time_input, str):
        # Try parsing as ISO 8601 first (most robust)
        try:
            dt_object = datetime.fromisoformat(time_input.replace('Z', '+00:00')) # Handle 'Z' explicitly
            if dt_object.tzinfo is None or dt_object.tzinfo.utcoffset(dt_object) is None:
                # If fromisoformat results in naive (e.g. no Z or offset), assume UTC
                dt_object_utc = dt_object.replace(tzinfo=timezone.utc)
            else:
                dt_object_utc = dt_object.astimezone(timezone.utc)
        except ValueError:
            # Try parsing with other known custom formats
            custom_formats_to_try = [
                '%Y-%m-%d %H:%M:%S',        # Your previous format
                '%Y-%m-%d %H:%M:%S.%f',    # With microseconds
                '%Y/%m/%d %H:%M:%S',
                '%d-%m-%Y %H:%M:%S',
                # Add more formats if you expect them
            ]
            parsed_successfully = False
            for fmt in custom_formats_to_try:
                try:
                    # strptime creates naive datetimes, so assume UTC
                    dt_naive = datetime.strptime(time_input, fmt)
                    dt_object_utc = dt_naive.replace(tzinfo=timezone.utc)
                    parsed_successfully = True
                    break
                except ValueError:
                    continue
            if not parsed_successfully:
                raise ValueError(
                    f"String '{time_input}' could not be parsed as ISO 8601 or any known custom format."
                )
    else:
        raise TypeError(
            f"Unsupported input type for time conversion: {type(time_input)}"
        )

    if dt_object_utc is None: # Should not happen if logic above is complete
        raise ValueError(f"Could not convert input '{time_input}' to a UTC datetime object.")

    # Return in ISO format. Using .replace for 'Z' is common for pure UTC.
    return dt_object_utc.isoformat().replace('+00:00', 'Z')