import httpx


def is_retryable_error(exception: BaseException) -> bool:
    """Determines if an exception should trigger a retry attempt."""

    # Network errors are retryable
    if isinstance(exception, (httpx.ConnectError, httpx.TimeoutException, httpx.RequestError)):
        return True

    # HTTP status errors - only retry server errors and rate limits
    if isinstance(exception, httpx.HTTPStatusError):
        status_code = exception.response.status_code
        return status_code >= 500 or status_code == 429

    return False
