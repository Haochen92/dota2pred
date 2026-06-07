from .api_clients.opendota_api import fetch_opendota_free_then_paid
from dota_oracle_common.models.match import ProMatchAPIResponse, ProMatchOutcome
from dota_oracle_common.utils.set_logging import get_logger
from typing import List
from pydantic import ValidationError
import aiohttp

logger = get_logger(__name__)

# A finished pro match is normally on the first page or two of the /proMatches feed, so a
# tiny page budget covers all fresh matches. Bounding the pagination keeps the FREE endpoint
# from being walked back through history (which exhausts the free tier's daily/per-minute
# quota -> HTTP 429) whenever a stale match widens the id-range. At 2 pages * one call/page
# every 2 min that is at most ~1.4k calls/day, well under the free cap. Matches not found in
# this window are left for the paid per-match StaleMatchService fallback, preserving the
# "free-first, paid only for the stale tail" design.
DEFAULT_MAX_PAGES = 2


async def fetch_pro_match(
    max_match_id: int, min_match_id: int, max_pages: int = DEFAULT_MAX_PAGES
) -> List[ProMatchOutcome]:
    output_list: List[ProMatchOutcome] = []
    pages_fetched = 0

    while max_match_id > min_match_id:
        if pages_fetched >= max_pages:
            logger.info(
                f"fetch_pro_match: reached max_pages={max_pages} (paged down to {max_match_id}); "
                "older matches left for the per-match stale fallback."
            )
            break
        try:
            res = await fetch_opendota_free_then_paid(
                endpoint="proMatches", params={"less_than_match_id": max_match_id}
            )
            pages_fetched += 1
            logger.info(f"fetching api endpoint for less_than_match_id: {max_match_id}")

            api_response = ProMatchAPIResponse.model_validate(res)
            list_instances = api_response.root
            if not list_instances:
                break

            list_match_ids = [instance.match_id for instance in list_instances]
            max_match_id = min(list_match_ids)

            output_list.extend(list_instances)

        except aiohttp.ClientResponseError as cre:
            # Rate limited on the free tier: a best-effort outcome lookup should degrade,
            # not fail. Return what we have; the next 2-min cycle and the paid per-match
            # StaleMatchService fallback resolve anything we couldn't reach this pass.
            if cre.status == 429:
                logger.warning(
                    f"fetch_pro_match: hit OpenDota rate limit (429); returning {len(output_list)} "
                    "partial results, stale fallback will cover the rest."
                )
                break
            logger.error(f"{type(cre).__name__}: {str(cre)}", exc_info=True)
            raise
        except (
            aiohttp.ClientConnectionError,
            aiohttp.ClientError,
            aiohttp.http.HttpProcessingError,
            ValueError,
            ValidationError,
        ) as e:
            error_message = f"{type(e).__name__}: {str(e)}"
            logger.error(error_message, exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Exception while fetching promatches, {e}", exc_info=True)
            raise

    return output_list
