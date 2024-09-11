import pytest
from middlewares.track_api import track_api_calls, YAML_FILE_PATH, APILimitExceededError
from unittest.mock import MagicMock
from datetime import datetime

@pytest.mark.parametrize(
    "initial_count, expected_count, raise_error, last_reset_date, current_date_str",
    [
        (5, 6, False, "20240901", "20240915"),         # Case where the count should increment on a non-reset day
        (100000, 100000, True, "20240901", "20240915"), # Case where the API limit should trigger an error
        (5, 0, False, "20240831", "20240901"),         # Case where the counter should reset on the first day of the month
    ]
)
def test_track_api_calls(mocker, initial_count, expected_count, raise_error, last_reset_date, current_date_str):
    # Mock the FileLock class
    mocker.patch("middlewares.track_api.FileLock")
    
    # Mock the file operations (reading and writing to YAML file)
    mock_open = mocker.patch("middlewares.track_api.open", mocker.mock_open())
    
    # Mock yaml.safe_load to return the initial count and last reset date
    mocker.patch("middlewares.track_api.yaml.safe_load", return_value={"count": initial_count, "last_reset_date": last_reset_date})
    
    # Mock yaml.safe_dump to capture the output
    mock_yaml_dump = mocker.patch("middlewares.track_api.yaml.safe_dump")
    
    # Mock the logger to verify error logging
    mock_logger = mocker.patch("middlewares.track_api.logger")
    
    # Mock datetime to control the current date
    mock_datetime = mocker.patch("middlewares.track_api.datetime", wraps=datetime)
    mock_datetime.now.return_value = datetime.strptime(current_date_str, "%Y%m%d")
    
    # Define a mock API function to be decorated
    @track_api_calls
    def mock_api_function():
        mock_response = MagicMock()
        mock_response.status_code = 200
        return mock_response
    
    # Test the behavior when the API limit is exceeded
    if raise_error:
        with pytest.raises(APILimitExceededError) as exc_info:
            mock_api_function()
        assert str(exc_info.value) == "API usage limit exceeded"
        mock_logger.error.assert_called_once_with("API Limit Exceeded")
        return
    else:
        response = mock_api_function()
        assert response.status_code == 200
    
    # Assertions to ensure file was opened and the correct count was written back
    mock_open.assert_any_call(YAML_FILE_PATH, 'r')
    mock_open.assert_any_call(YAML_FILE_PATH, 'w')
    mock_yaml_dump.assert_called_once()
    
    # Prepare the expected YAML output
    expected_yaml = {"count": expected_count}
    if current_date_str.endswith("01") and last_reset_date != current_date_str:
        expected_yaml["last_reset_date"] = current_date_str
        previous_date_str = (datetime.strptime(current_date_str, "%Y%m%d") - timedelta(days=1)).strftime('%Y%m%d')
        expected_yaml[previous_date_str] = initial_count if initial_count < API_CALL_LIMIT else API_CALL_LIMIT
    
    # Assert that the correct data was written to the YAML file
    mock_yaml_dump.assert_called_with(expected_yaml, mock_open())
