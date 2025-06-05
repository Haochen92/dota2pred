from typing import Dict, List
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
            
                