from dota_oracle.data_extraction.fetch_match_details import fetch_match_details
from dota_oracle.models.match import MatchesAPIResponse
from dota_oracle.models.redis.schema import StreamMatchEventData, FailureRecord
from dota_oracle.utils.set_logging import get_logger
from typing import Dict, Any, Set, Coroutine, List
from .history_update_service import HistoryUpdateService
from ..redis_service import RedisService
from dota_oracle.data_repository.match_repository import MatchRepository
from dota_oracle.models.match import MatchOutcomeTable
from dota_oracle.constants.redis_constants import STREAM_PENDING_COMPLETION, COMPLETION_GROUP
from dota_oracle.utils.time_utils import get_current_utc_iso_timestamp
from dota_oracle.utils.async_utils import get_outcome_concurrently, run_updates_as_group
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession


class CompletedMatchService:
    def __init__(self, engine: AsyncEngine)