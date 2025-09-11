import httpx
import os
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
from dota_oracle_common.utils.env_loader import load_workspace_env
from dota_oracle_common.utils.set_logging import get_logger
from dota_oracle_common.models.match import MatchNotifcationAPIPayload
from dota_oracle_common.repositories.match_repository import MatchRepository
from ..redis_services.redis_service import RedisService
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from dota_oracle_pipeline.data_transformation.api_payload_parser import map_match_table_to_notification_payload
from dota_oracle_common.utils.retry_utils import is_retryable_error
from dota_oracle_common.models.api import LiveStateUpdateRequest

from typing import Set, List, Dict, Any

logger = get_logger(__name__)
load_workspace_env()

API_SERVICE_URL = os.getenv("API_SERVICE_URL", "http://api-service:8000")


class NotificationService:
    def __init__(
        self,
        redis_service: RedisService,
        db_session_factory: async_sessionmaker[AsyncSession],
        http_client: httpx.AsyncClient,
    ):
        self.redis_service = redis_service
        self.local_session = db_session_factory
        self.http_client = http_client

    async def notify_state_change(self) -> Dict[str, Any]:
        """Sends live match data to the API service using the shared http_client."""
        logger.info("Starting notification process for state changes...")
        final_request_payload = LiveStateUpdateRequest(live_matches=[])

        try:
            live_match_set = await self.redis_service.get_live_match_ids()

            if live_match_set:
                logger.info(f"Found {len(live_match_set)} live matches. Fetching full payloads.")
                match_payloads = await self._fetch_match_payloads(live_match_set)
                final_request_payload = LiveStateUpdateRequest(live_matches=match_payloads)

            logger.info(f"Sending notification payload with {len(final_request_payload.live_matches)} matches.")
            api_response = await self.call_api_endpoint(final_request_payload)

            logger.info("Successfully sent status update to API service.")
            return {"successful": True, "status_code": api_response.get("status_code")}

        except (httpx.RequestError, httpx.HTTPStatusError) as exc:
            logger.error(f"Failed to send notification after all attempts. Error: {exc}", exc_info=True)
            return {"successful": False, "error": str(exc)}

        except Exception as e:
            logger.error(f"A critical error occurred in the notification process: {e}", exc_info=True)
            return {"successful": False, "error": f"An unexpected error occurred: {e}"}

    async def _fetch_match_payloads(self, matches_to_fetch: Set[int]) -> List[MatchNotifcationAPIPayload]:
        """Fetches match details from database."""
        logger.debug(f"Fetching payload details for match IDs: {matches_to_fetch}")
        async with self.local_session() as session:
            match_repo = MatchRepository(session=session)
            full_match_details = await match_repo.get_match_details(
                input_id_list=list(matches_to_fetch), relationship_fields=["predictions", "league_data"]
            )

            if not full_match_details:
                logger.warning("Live match IDs were provided, but no corresponding matches found in DB.")
                return []

            return [map_match_table_to_notification_payload(match) for match in full_match_details]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception(is_retryable_error),
        reraise=True,
    )
    async def call_api_endpoint(self, payload: LiveStateUpdateRequest) -> Dict[str, Any]:
        """Sends notification payload to API service with automatic retry on network failures."""
        notification_endpoint = f"{API_SERVICE_URL}/streaming/live-state-update"

        try:
            response = await self.http_client.post(notification_endpoint, json=payload.model_dump(mode="json"))
            response.raise_for_status()

            logger.info(f"Successfully sent live state update. Status: {response.status_code}")
            return {"status_code": response.status_code}

        except httpx.HTTPStatusError as exc:
            logger.error(f"API service returned an error: {exc.response.status_code} {exc.response.text}")
            raise

        except httpx.RequestError as exc:
            logger.warning(f"Network error during API call, will retry... Error: {exc}")
            raise
