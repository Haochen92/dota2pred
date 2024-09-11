from filelock import FileLock
import yaml
from src.config import ROOT_DIR
from datetime import datetime, timedelta
from src.utils.set_logging import get_logger


logger = get_logger(__name__)

LOCK_FILE_PATH = ROOT_DIR / "constants" / "api_usage.yml.lock"
YAML_FILE_PATH = ROOT_DIR / "constants" / "api_usage.yml"

API_CALL_LIMIT = 150000

class APILimitExceededError(Exception):
    def __init__(self):
        self.message = "API usage limit exceeded"
        self.code = "API_LIMIT_EXCEEDED"
        super().__init__(self.message)

def track_api_calls(func):
    async def async_wrapper(*args, **kwargs):
        # Acquire lock
        try:
            lock = FileLock(LOCK_FILE_PATH, timeout=10)
        except:
            logger.error("failed to acquire file lock after multiple attempts.")
            raise e
        
        with lock:
            try:
                # Load the current API usage data
                with open(YAML_FILE_PATH, 'r') as file:
                    api_usage = yaml.safe_load(file) or {}
            except FileNotFoundError:
                api_usage = {}
                logger.warning("API usage YAML file not found. A new file will be created.")
            except yaml.YAMLError as e:
                logger.error(f"Error reading the YAML file: {e}")
                raise e
            except Exception as e:
                logger.error(f"Unexpected error while writing to YAML file: {e}")
                raise e

            # Check if the API limit has been exceeded
            if api_usage.get('count', 0) >= API_CALL_LIMIT:
                logger.error("API Limit Exceeded")
                raise APILimitExceededError()

            # Reset the counter on the first day of the month
            current_date_str = datetime.now().strftime('%Y%m%d')
            if current_date_str.endswith("01"):
                last_reset_date = api_usage.get('last_reset_date')
                
                if last_reset_date != current_date_str:
                    previous_date_str = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
                    api_usage[previous_date_str] = api_usage.get('count', 0)
                    api_usage['count'] = 0
                    api_usage['last_reset_date'] = current_date_str
                    logger.info(f"API usage counter reset for the new month: {current_date_str}")

            # Call the original function
            try:
                status, json_data = await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"An error occured in the wrapped function: {func.__name__}: {e}")
                raise e

            # Update the counter if the response is successful
            if status != 500:
                api_usage['count'] = api_usage.get('count', 0) + 1
                if api_usage['count'] % 100 == 0:
                    logger.info(f"API usage updated: {api_usage}")

            # Save the updated API usage data
            try:
                with open(YAML_FILE_PATH, 'w') as file:
                    yaml.safe_dump(api_usage, file)
            except yaml.YAMLError as e:
                logger.error(f"Error writing to the YAML file: {e}")

        return status, json_data
    return async_wrapper
