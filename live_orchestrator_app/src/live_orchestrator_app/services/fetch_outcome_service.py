from typing import Dict, List
from dota_oracle_common.utils.set_logging import get_logger
from dota_oracle_pipeline.data_extraction.api_clients.opendota_api import OpenDotaClient
from dota_oracle_pipeline.data_extraction.fetch_pro_match import fetch_pro_match

# Config logging
logger = get_logger(__name__)


class FetchOutcomeService:
    def __init__(self, opendota_client: OpenDotaClient):
        self.opendota_client = opendota_client

    async def fetch_outcomes_batch(self, completed_match_ids: List[int]) -> Dict[int, bool]:
        if not completed_match_ids:
            logger.warning("No complete matches to process")

        max_match_id, min_match_id = (
            max(completed_match_ids) + 1,
            min(completed_match_ids),
        )  # +1 to include the latest match as well
        try:
            pro_match_instances = await fetch_pro_match(
                max_match_id,
                min_match_id,
                opendota_client=self.opendota_client,
            )

            if not pro_match_instances:
                logger.info(f"no completed matches between match_ids: {min_match_id} - {max_match_id}")
                return {}

            outcome_dict = {instance.match_id: instance.radiant_win for instance in pro_match_instances}

            logger.info(f"Found {len(outcome_dict)} matches between match: {max_match_id} - {min_match_id}")
            return outcome_dict
        except Exception as e:
            error_msg = (
                f"Exception occurred while trying to collect promatch outcome "
                f"between match-ids: {min_match_id} - {max_match_id}"
            )
            logger.error(error_msg, exc_info=True)
            raise e
