from dotenv import load_dotenv, find_dotenv
from dota_oracle_common.utils import get_logger

logger = get_logger(__name__)


def load_workspace_env() -> None:
    env_file = find_dotenv(".env")
    if env_file:
        load_dotenv(env_file)
