"""
Contract test for OpenDota Explorer endpoint via our helper.
Makes real network calls; retries a few times to smooth over transient errors.
"""

import pytest
from datetime import datetime, timezone, timedelta
from tenacity import retry, wait_fixed, stop_after_attempt

from dota_oracle_pipeline.data_extraction.opendota_explorer import find_match_id_by_timestamp


pytestmark = [pytest.mark.asyncio, pytest.mark.contract]

wait_duration = 20


@retry(stop=stop_after_attempt(3), wait=wait_fixed(wait_duration))
async def test_explorer_contract_returns_match_id() -> None:
    # Use a recent timestamp to increase odds of data proximity
    ts = datetime.now(timezone.utc) - timedelta(days=7)
    match_id = await find_match_id_by_timestamp(ts)

    assert match_id is not None, "Explorer should return a match_id for a valid timestamp"
    assert isinstance(match_id, int)
    assert match_id > 0
