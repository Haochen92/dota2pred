from typing import AsyncGenerator, List, Optional

from dota_oracle_common.models.match import PublicMatch, PublicMatchAPIResponse
from dota_oracle_common.utils import get_logger
from .api_clients.opendota_api import (
    fetch_opendota_api_uncached,
    fetch_opendota,
)


logger = get_logger(__name__)

# OpenDota endpoints
API_ENDPOINT_PUBLIC_MATCHES = "publicMatches"


async def fetch_public_matches_page(
    *,
    less_than_match_id: Optional[int],
    min_rank: int,
    max_rank: int,
) -> List[PublicMatch]:
    """
    Fetch a single page of public matches using OpenDota.

    Attempts the paid API first (if API key is present), otherwise falls back to the free endpoint.
    """
    params = {"less_than_match_id": less_than_match_id, "min_rank": min_rank, "max_rank": max_rank}
    params = {k: v for k, v in params.items() if v is not None}

    try:
        # Use the uncached paid endpoint to avoid stale pages across passes
        res = await fetch_opendota_api_uncached(endpoint=API_ENDPOINT_PUBLIC_MATCHES, params=params)
    except ValueError:
        res = await fetch_opendota(endpoint=API_ENDPOINT_PUBLIC_MATCHES, params=params)

    parsed = PublicMatchAPIResponse.model_validate(res)
    return parsed.root


async def stream_public_matches(
    *,
    start_less_than_match_id: Optional[int],
    min_rank: int,
    max_rank: int,
    error_hop_match_ids: int = 5000,
    hop_max: int = 40000,
    stop_at_match_id: Optional[int] = None,
) -> AsyncGenerator[PublicMatch, None]:
    """
    Stream PublicMatch records via OpenDota's /publicMatches endpoint.

    - Paginates backwards using `less_than_match_id`.
    - If `start_less_than_match_id` is None, fetches the most recent page.
    - On API failure, logs error and "hops" backwards by `error_hop_match_ids`.
    - Stops when an empty page is returned.
    - Filters by `avg_rank_tier` if present in payload.
    """
    cursor: Optional[int] = start_less_than_match_id
    hop_current = max(1, error_hop_match_ids)

    while True:
        # Early stop if we've crossed the lower boundary without seeing any data
        if stop_at_match_id is not None and cursor is not None and cursor <= stop_at_match_id:
            logger.info(f"Cursor {cursor} <= stop_at_match_id {stop_at_match_id}; stopping stream at boundary.")
            break
        try:
            batch = await fetch_public_matches_page(less_than_match_id=cursor, min_rank=min_rank, max_rank=max_rank)
        except Exception as e:
            logger.error(
                f"Error fetching /publicMatches at cursor={cursor}. Hopping back by {hop_current}. Error: {e}",
                exc_info=True,
            )
            if cursor is None:
                # If we failed on the very first call with None, try a best-effort large cursor hop
                cursor = max(0, 9_999_999_999_999 - hop_current)
            else:
                cursor = max(0, cursor - hop_current)
            # Exponential backoff on hop size, capped
            hop_current = min(hop_current * 2, hop_max)
            continue

        if not batch:
            # Some cursors (especially older ranges) may intermittently return empty pages
            # even though earlier pages exist. Hop the cursor backward and retry instead of stopping.
            # If we've reached the beginning (cursor==0) or have no cursor context, stop.
            if cursor is None or cursor == 0:
                logger.warning(
                    "/publicMatches returned an empty page at cursor with no further hop context; stopping stream."
                )
                break
            logger.warning(f"/publicMatches empty page at cursor={cursor}. Hopping back by {hop_current} and retrying.")
            cursor = max(0, cursor - hop_current)
            hop_current = min(hop_current * 2, hop_max)
            # If we've now moved past the lower boundary, stop.
            if stop_at_match_id is not None and cursor <= stop_at_match_id:
                logger.info(
                    f"Cursor {cursor} reached stop_at_match_id {stop_at_match_id} after empty pages; stopping stream."
                )
                break
            continue

        try:
            min_in_batch = min(m.match_id for m in batch)
        except ValueError:
            logger.warning("Received batch without match_ids; stopping stream.")
            break

        # Successful page fetch: reset hop size to initial
        hop_current = max(1, error_hop_match_ids)

        for item in batch:
            # Defensive client side filtering
            if item.avg_rank_tier is not None:
                if item.avg_rank_tier < min_rank or item.avg_rank_tier > max_rank:
                    continue
            yield item

        cursor = min_in_batch
