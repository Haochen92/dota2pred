import time
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace

import pytest
from unittest.mock import AsyncMock, MagicMock

from dota_oracle_common.models.redis.schema import ConsumedEvent, OddsPayload
from dota_oracle_common.models.odds import MarketSnapshot, SideQuote, OddsSkipReason
from live_orchestrator_app.services.odds_market_service import OddsMarketService

MOD = "live_orchestrator_app.services.odds_market_service"

WINDOW = 360


class _FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _session_factory():
    return _FakeSession()


def _event(match_id: int = 111, seconds_ago: int = 0) -> ConsumedEvent[OddsPayload]:
    ms = int((time.time() - seconds_ago) * 1000)
    return ConsumedEvent[OddsPayload](
        match_id=match_id, event_id=f"{ms}-0", payload=OddsPayload(match_id=match_id, radiant_win=True)
    )


def _match(
    match_id: int = 111,
    radiant_team_id: int = 1,
    dire_team_id: int = 2,
    radiant_name="Tundra",
    dire_name="Team Spirit",
) -> SimpleNamespace:
    return SimpleNamespace(
        match_id=match_id,
        radiant_team_id=radiant_team_id,
        dire_team_id=dire_team_id,
        radiant_name=radiant_name,
        dire_name=dire_name,
        start_time=datetime.now(timezone.utc) - timedelta(seconds=60),
    )


def _mapping(steam_team_id: int, slug: str) -> SimpleNamespace:
    return SimpleNamespace(
        steam_team_id=steam_team_id, polymarket_slug=slug, canonical_name=slug.replace("-", " ").title()
    )


def _snapshot() -> MarketSnapshot:
    return MarketSnapshot(
        event_slug="blast-slam",
        market_slug="tundra-vs-spirit-game-1",
        condition_id="0xabc",
        side_a=SideQuote(token_id="tok_r", best_bid=0.60, best_ask=0.62, liquidity=9000),
        side_b=SideQuote(token_id="tok_d", best_bid=0.38, best_ask=0.40, liquidity=8000),
        raw={"market": {"slug": "tundra-vs-spirit-game-1"}},
    )


def _patch_db(mocker, matches, mappings) -> None:
    mocker.patch(f"{MOD}.MatchRepository", return_value=MagicMock(get_match_details=AsyncMock(return_value=matches)))
    mocker.patch(f"{MOD}.OddsRepository", return_value=MagicMock(get_team_mappings=AsyncMock(return_value=mappings)))


def _service(client) -> OddsMarketService:
    return OddsMarketService(
        db_session_factory=_session_factory, polymarket_client=client, snapshot_window_seconds=WINDOW
    )


@pytest.mark.asyncio
async def test_resolves_to_snapshot_with_prices(mocker) -> None:
    _patch_db(mocker, [_match()], [_mapping(1, "tundra"), _mapping(2, "spirit")])
    client = AsyncMock()
    client.get_market_snapshot = AsyncMock(return_value=_snapshot())

    results = await _service(client).resolve_snapshots([_event()])

    assert len(results) == 1
    payload = results[0].payload
    assert payload.skip_reason is None
    assert payload.market_slug == "tundra-vs-spirit-game-1"
    assert payload.a_best_ask == 0.62
    assert payload.b_best_bid == 0.38
    assert payload.game_time_seconds is not None and payload.game_time_seconds >= 0


@pytest.mark.asyncio
async def test_no_mapping_falls_back_to_steam_name(mocker) -> None:
    # No team-map entries at all, but the match carries team names -> still resolves via the names
    # (the map is an optional alias override, not a required gate).
    _patch_db(mocker, [_match()], [])
    client = AsyncMock()
    client.get_market_snapshot = AsyncMock(return_value=_snapshot())

    results = await _service(client).resolve_snapshots([_event()])

    assert len(results) == 1
    assert results[0].payload.skip_reason is None
    client.get_market_snapshot.assert_called_once()
    # The Steam names were passed as candidate aliases.
    radiant_aliases, dire_aliases = client.get_market_snapshot.call_args.args
    assert "Tundra" in radiant_aliases and "Team Spirit" in dire_aliases


@pytest.mark.asyncio
async def test_no_name_and_no_mapping_skips(mocker) -> None:
    # Anonymous team (no name) and no map alias -> nothing to match on -> skip, no network call.
    _patch_db(mocker, [_match(radiant_name=None, dire_name=None)], [])
    client = AsyncMock()
    client.get_market_snapshot = AsyncMock(return_value=_snapshot())

    results = await _service(client).resolve_snapshots([_event()])

    assert len(results) == 1
    assert results[0].payload.skip_reason == OddsSkipReason.NO_MARKET_FOUND
    client.get_market_snapshot.assert_not_called()


@pytest.mark.asyncio
async def test_client_returns_none_records_skip(mocker) -> None:
    _patch_db(mocker, [_match()], [_mapping(1, "tundra"), _mapping(2, "spirit")])
    client = AsyncMock()
    client.get_market_snapshot = AsyncMock(return_value=None)

    results = await _service(client).resolve_snapshots([_event()])

    assert len(results) == 1
    assert results[0].payload.skip_reason == OddsSkipReason.NO_MARKET_FOUND


@pytest.mark.asyncio
async def test_transient_error_within_window_left_pending(mocker) -> None:
    _patch_db(mocker, [_match()], [_mapping(1, "tundra"), _mapping(2, "spirit")])
    client = AsyncMock()
    client.get_market_snapshot = AsyncMock(side_effect=RuntimeError("network blip"))

    # Fresh event (age ~0 < window) -> omitted so it stays pending for a retry next cycle.
    results = await _service(client).resolve_snapshots([_event(seconds_ago=0)])
    assert results == []


@pytest.mark.asyncio
async def test_transient_error_past_window_records_skip(mocker) -> None:
    _patch_db(mocker, [_match()], [_mapping(1, "tundra"), _mapping(2, "spirit")])
    client = AsyncMock()
    client.get_market_snapshot = AsyncMock(side_effect=RuntimeError("still down"))

    # Aged event (older than the window) -> give up and record a no-market skip.
    results = await _service(client).resolve_snapshots([_event(seconds_ago=WINDOW + 60)])
    assert len(results) == 1
    assert results[0].payload.skip_reason == OddsSkipReason.NO_MARKET_FOUND
