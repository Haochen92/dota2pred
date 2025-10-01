from datetime import datetime, timezone
from typing import Optional

from dota_oracle_common.utils import get_logger
from .api_clients.opendota_api import fetch_opendota_api, fetch_opendota


logger = get_logger(__name__)

API_ENDPOINT_EXPLORER = "explorer"


async def find_match_id_by_timestamp(target_time: datetime) -> Optional[int]:
    """
    Use OpenDota /explorer to find the match_id with start_time closest to the given timestamp.
    Returns None on failure or if no rows are found.
    """
    try:
        epoch = int(target_time.replace(tzinfo=timezone.utc).timestamp())
        sql = f"SELECT match_id FROM matches ORDER BY ABS(start_time - {epoch}) ASC LIMIT 1"
        params = {"sql": sql}
        try:
            res = await fetch_opendota_api(endpoint=API_ENDPOINT_EXPLORER, params=params)
        except ValueError:
            res = await fetch_opendota(endpoint=API_ENDPOINT_EXPLORER, params=params)

        rows = res.get("rows") if isinstance(res, dict) else None
        if not rows:
            logger.warning(f"No rows returned from /explorer for epoch {epoch}")
            return None
        match_id = rows[0].get("match_id")
        if match_id is None:
            return None
        return int(match_id)
    except Exception as e:
        logger.error(f"Failed to find match_id by timestamp: {e}", exc_info=True)
        return None

