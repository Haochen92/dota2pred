"""
Contract Testing - validate the live Polymarket Gamma/CLOB response shapes against the parser the
odds-capture stage relies on. Skips gracefully when no Dota event is currently open (the schedule,
not a regression). Run with: pytest -m contract.
"""

import pytest
import httpx
from tenacity import retry, wait_fixed, stop_after_attempt

from dota_oracle_common.constants.endpoint_configs import service_url
from dota_oracle_pipeline.data_extraction.api_clients.polymarket_client import PolymarketClient

pytestmark = [pytest.mark.asyncio, pytest.mark.contract]

wait_duration = 20


def _client(http: httpx.AsyncClient) -> PolymarketClient:
    return PolymarketClient(
        http_client=http,
        gamma_url=service_url.BASE_GAMMA_URL,
        clob_url=service_url.BASE_CLOB_URL,
        tag_slug=service_url.ODDS_DOTA_TAG_SLUG,
    )


@retry(stop=stop_after_attempt(3), wait=wait_fixed(wait_duration))
async def test_gamma_events_endpoint_contract() -> None:
    """The Gamma /events?tag_slug=dota-2 discovery returns a list, and any per-game market we pick
    exposes the fields the parser depends on (sportsMarketType, outcomes, clobTokenIds, conditionId)."""
    async with httpx.AsyncClient(timeout=30.0) as http:
        client = _client(http)
        events = await client._discover_events()

        assert isinstance(events, list), f"expected list of events, got {type(events).__name__}"
        if not events:
            pytest.skip("No open Dota events on Polymarket right now; endpoint shape OK (returned a list).")

        for _event_slug, market in client._candidate_game_markets(events):
            assert market.get("sportsMarketType") == "child_moneyline"
            assert client._parse_outcomes(market), "game market should expose two outcomes"
            assert client._parse_token_ids(market), "game market should expose clobTokenIds"
            assert market.get("conditionId"), "game market should expose conditionId"


@retry(stop=stop_after_attempt(3), wait=wait_fixed(wait_duration))
async def test_clob_book_endpoint_contract() -> None:
    """The CLOB /book?token_id= shape is parseable by _best and yields prices within [0, 1]."""
    async with httpx.AsyncClient(timeout=30.0) as http:
        client = _client(http)
        events = await client._discover_events()
        candidates = client._candidate_game_markets(events) if events else []
        if not candidates:
            pytest.skip("No open Dota game markets right now; cannot exercise the CLOB book contract.")

        token_id = client._parse_token_ids(candidates[0][1])[0]
        book = await client._fetch_book(token_id)

    assert isinstance(book, dict), "order book should be a dict"
    best_bid, best_ask, liquidity = PolymarketClient._best(book)
    assert 0.0 <= best_bid <= 1.0
    assert 0.0 <= best_ask <= 1.0
    assert liquidity >= 0.0
