from dota_oracle.data_extraction.fetch_match_details import fetch_match_details
from dota_oracle.data_extraction.api_clients.opendota_api import fetch_opendota
from dota_oracle.models.match import MatchesAPIResponse
from dota_oracle.models.redis.schema import StreamMatchEventData, FailureRecord
from dota_oracle.utils.set_logging import get_logger
from typing import Dict, Any, Set, Coroutine, List, Dict
from .history_update_service import HistoryUpdateService
from ..redis_service import RedisService
from dota_oracle.data_repository.match_repository import MatchRepository
from dota_oracle.models.match import MatchOutcomeTable
from dota_oracle.constants.redis_constants import STREAM_PENDING_COMPLETION, COMPLETION_GROUP
from dota_oracle.utils.time_utils import get_current_utc_iso_timestamp
from dota_oracle.utils.async_utils import get_outcome_concurrently, run_updates_as_group
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from dota_oracle.utils.set_logging import get_logger
from dota_oracle.data_extraction.fetch_pro_match import fetch_pro_match

# Config logging
logger = get_logger(__name__)

class FetchOutcomeService:
    @staticmethod        
    async def fetch_outcomes_batch(completed_match_ids: List[int]) -> Dict[int, bool]:
        if not completed_match_ids:
            logger.warning("No complete matches to process")
        
        max_match_id, min_match_id = max(completed_match_ids), min(completed_match_ids)
        try:
            pro_match_instances = await fetch_pro_match(max_match_id, min_match_id)
            
            if not pro_match_instances:
                logger.warning(f"no completed matches between match_ids: {min_match_id} - {max_match_id}")
                return {}
            
            outcome_dict = {instance.match_id : instance.radiant_win for instance in pro_match_instances}
            return outcome_dict
        except Exception as e:
            error_msg = (
                f"Exception occurred while trying to collect promatch outcome "
                f"between match-ids: {min_match_id} - {max_match_id}"
            )
            logger.error(error_msg, exc_info=True)
            raise e
            
                