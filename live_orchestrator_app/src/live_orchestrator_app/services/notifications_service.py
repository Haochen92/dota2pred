import httpx
import os
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from dota_oracle_common.utils.env_loader import load_workspace_env
from dota_oracle_common.utils.set_logging import get_logger
from dota_oracle_common.models.match import MatchNotifcationAPIPayload
from dota_oracle_common.repositories.match_repository import MatchRepository
from ..redis_services.redis_service import RedisService
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from dota_oracle_pipeline.data_transformation.api_payload_parser import map_match_table_to_notification_payload

from typing import Set, List, Dict, Any

logger = get_logger(__name__)
load_workspace_env()

API_SERVICE_URL = os.getenv("API_SERVICE_URL", "http://api-service:8000")


class NotificationService:
    def __init__(self, redis_service: RedisService, db_session_factory: async_sessionmaker[AsyncSession]):
        self.redis_service = redis_service
        self.local_session = db_session_factory
        self.http_client = httpx.AsyncClient(base_url=API_SERVICE_URL, timeout=10.0)

    async def notify_state_change(self) -> Dict[str, Any]:
        """
        Sends live match data to the API service.

        Always sends a payload (empty if no live matches) to maintain consistent
        API contract and enable downstream systems to detect state changes.

        Returns:
            Dict containing notification status and error information if applicable.

        Raises:
            Exception: On critical failures (Redis/DB errors) to fail the parent flow.
        """
        logger.info("Starting notification process for state changes...")
        final_payload = {"live_matches": []}

        try:
            live_match_set = await self.redis_service.get_live_match_ids()

            if live_match_set:
                logger.info(f"Found {len(live_match_set)} live matches. Fetching full payloads.")
                match_payloads = await self.fetch_match_payloads(live_match_set)
                final_payload["live_matches"] = [p.model_dump() for p in match_payloads]

            logger.info(f"Sending notification payload with {len(final_payload['live_matches'])} matches.")
            notification_status = await self.call_api_endpoint(final_payload)

            return notification_status

        except Exception as e:
            logger.error(f"A critical error occurred before notification could be sent: {e}", exc_info=True)
            raise

    async def fetch_match_payloads(self, matches_to_fetch: Set[int]) -> List[MatchNotifcationAPIPayload]:
        """
        Fetches match details from database and converts to notification payload format.

        Args:
            matches_to_fetch: Set of match IDs to retrieve from database.

        Returns:
            List of notification payload objects ready for API transmission.

        Raises:
            Exception: On database errors to enable fail-fast behavior.
        """
        logger.debug(f"Fetching payload details for match IDs: {matches_to_fetch}")
        async with self.local_session() as session:
            match_repo = MatchRepository(session=session)
            full_match_details = await match_repo.get_match_details(
                input_id_list=list(matches_to_fetch), relationship_fields=["predictions"]
            )

            if not full_match_details:
                logger.warning("Live match IDs were provided, but no corresponding matches found in DB.")
                return []

            return [map_match_table_to_notification_payload(match) for match in full_match_details]

    async def call_api_endpoint(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sends notification payload to API service with automatic retry on network failures.

        HTTP status errors (4xx/5xx) are not retried as they indicate client/server
        issues that won't resolve with retry attempts.

        Args:
            payload: The notification data to send to the API service.

        Returns:
            Dict containing success status, HTTP status code, and error details.
        """
        try:
            result = await self._call_api_with_retry(payload)

            # Handle case where tenacity returns None after exhausting retries
            if result is None:
                return {
                    "successful": False,
                    "status_code": None,
                    "error": "Network request failed after all retry attempts",
                }

            return result
        except Exception:
            # Handle any remaining exceptions (like RetryError) after exhausting retries
            return {
                "successful": False,
                "status_code": None,
                "error": "Network request failed after all retry attempts",
            }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.RequestError),
        reraise=False,
    )
    async def _call_api_with_retry(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Internal method that handles the actual API call with retry logic."""
        notification_endpoint = "/internal/live-state-update"
        status = {"successful": False, "status_code": None, "error": None}

        try:
            response = await self.http_client.post(notification_endpoint, json=payload)
            response.raise_for_status()

            status["successful"] = True
            status["status_code"] = response.status_code
            logger.info(f"Successfully sent live state update. Status: {response.status_code}")

        except httpx.HTTPStatusError as exc:
            error_message = f"API service returned an error: {exc.response.status_code} {exc.response.text}"
            logger.error(error_message)
            status["status_code"] = exc.response.status_code
            status["error"] = error_message

        except httpx.RequestError as exc:
            # Network errors are retried by tenacity decorator
            error_message = f"A network error occurred: {exc}"
            logger.error(f"Attempt failed: {error_message}")
            status["error"] = error_message
            raise

        return status

    async def close(self):
        """Gracefully closes the HTTP client connection."""
        await self.http_client.aclose()
