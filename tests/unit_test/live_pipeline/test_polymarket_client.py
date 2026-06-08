import json

import pytest
from unittest.mock import AsyncMock, MagicMock

from dota_oracle_pipeline.data_extraction.api_clients.polymarket_client import PolymarketClient


def _client(http_client=None) -> PolymarketClient:
    return PolymarketClient(
        http_client=http_client or AsyncMock(),
        gamma_url="https://gamma.test",
        clob_url="https://clob.test",
        tag_slug="dota-2",
    )


def _game1_market() -> dict:
    return {
        "slug": "tundra-vs-spirit-game-1",
        "question": "Dota 2: Tundra vs Team Spirit - Game 1 Winner",
        "groupItemTitle": "Game 1 Winner",
        "sportsMarketType": "child_moneyline",
        "conditionId": "0xabc",
        "outcomes": json.dumps(["Tundra", " Team Spirit"]),  # note stray whitespace, as live data has
        "clobTokenIds": json.dumps(["tok_tundra", "tok_spirit"]),
        # Open-market flags: live data keeps active/enableOrderBook true even on resolved games,
        # so closed=False + acceptingOrders=True are the reliable "has a live book" signals.
        "closed": False,
        "acceptingOrders": True,
    }


def _series_market() -> dict:
    return {
        "slug": "tundra-vs-spirit-series",
        "question": "Dota 2: Tundra vs Team Spirit (BO3)",
        "groupItemTitle": "Match Winner",
        "sportsMarketType": "moneyline",
        "outcomes": json.dumps(["Tundra", "Team Spirit"]),
        "clobTokenIds": json.dumps(["tok_s_tundra", "tok_s_spirit"]),
    }


def _kills_market() -> dict:
    return {
        "slug": "tundra-vs-spirit-kills",
        "question": "Total Kills Over/Under 51.5 in Game 1?",
        "groupItemTitle": "Total Kills Over/Under",
        "sportsMarketType": "kill_over_under_game",
        "outcomes": json.dumps(["Over", "Under"]),
        "clobTokenIds": json.dumps(["tok_over", "tok_under"]),
    }


# --- pure helpers -------------------------------------------------------- #


def test_best_picks_max_bid_min_ask_ignoring_order() -> None:
    book = {
        "bids": [{"price": "0.40", "size": "100"}, {"price": "0.45"}],
        "asks": [{"price": "0.55"}, {"price": "0.52"}],
    }
    best_bid, best_ask, liquidity = PolymarketClient._best(book)
    assert best_bid == 0.45
    assert best_ask == 0.52
    assert liquidity == 100.0  # falls back to summed bid size when absent


def test_best_empty_book_is_untradeable_not_crash() -> None:
    best_bid, best_ask, liquidity = PolymarketClient._best({})
    assert best_bid == 0.0
    assert best_ask == 1.0
    assert liquidity == 0.0


def test_parse_token_ids_handles_json_string_and_list() -> None:
    assert PolymarketClient._parse_token_ids({"clobTokenIds": json.dumps(["a", "b"])}) == ["a", "b"]
    assert PolymarketClient._parse_token_ids({"clobTokenIds": ["a", "b"]}) == ["a", "b"]
    assert PolymarketClient._parse_token_ids({}) == []
    assert PolymarketClient._parse_token_ids({"clobTokenIds": "not-json"}) == []


def test_is_target_game_market_only_game1_child_moneyline() -> None:
    client = _client()
    assert client._is_target_game_market(_game1_market()) is True
    assert client._is_target_game_market(_series_market()) is False  # series moneyline
    assert client._is_target_game_market(_kills_market()) is False  # exotic market
    game2 = {**_game1_market(), "groupItemTitle": "Game 2 Winner"}
    assert client._is_target_game_market(game2) is False  # v1 is Game 1 only


def test_is_target_game_market_excludes_resolved_games() -> None:
    client = _client()
    # A resolved Game 1 in a still-active series: its token 404s on the CLOB, so it must be skipped.
    resolved = {**_game1_market(), "closed": True, "acceptingOrders": False}
    assert client._is_target_game_market(resolved) is False
    not_accepting = {**_game1_market(), "acceptingOrders": False}
    assert client._is_target_game_market(not_accepting) is False


def test_candidate_game_markets_flattens_and_filters() -> None:
    client = _client()
    events = [{"slug": "blast-slam", "markets": [_series_market(), _game1_market(), _kills_market()]}]
    candidates = client._candidate_game_markets(events)
    assert len(candidates) == 1
    event_slug, market = candidates[0]
    assert event_slug == "blast-slam"
    assert market["groupItemTitle"] == "Game 1 Winner"


def test_orient_tokens_maps_outcomes_to_radiant_dire() -> None:
    client = _client()
    oriented = client._orient_tokens(
        ["Team Spirit", "Tundra"],
        ["tok_spirit", "tok_tundra"],
        {"tundra", "Tundra"},  # radiant candidate names
        {"team-spirit", "Team Spirit"},  # dire candidate names
    )
    assert oriented == ("tok_tundra", "tok_spirit")


def test_orient_tokens_returns_none_when_unmappable() -> None:
    client = _client()
    assert client._orient_tokens(["Yes", "No"], ["t1", "t2"], {"tundra"}, {"spirit"}) is None


# --- end-to-end with a fake HTTP layer ----------------------------------- #


def _resp(payload, status_code: int = 200) -> MagicMock:
    r = MagicMock()
    r.status_code = status_code
    r.raise_for_status = MagicMock()
    r.json = MagicMock(return_value=payload)
    return r


@pytest.mark.asyncio
async def test_get_market_snapshot_resolves_game1_and_orients() -> None:
    event = {"slug": "blast-slam-2026", "markets": [_series_market(), _game1_market(), _kills_market()]}
    book_tundra = {"bids": [{"price": "0.60", "size": "500"}], "asks": [{"price": "0.62"}], "liquidity": 9000}
    book_spirit = {"bids": [{"price": "0.38"}], "asks": [{"price": "0.40"}], "liquidity": 8000}

    async def fake_get(url, params=None):
        if url.endswith("/events"):
            return _resp([event])
        token = params["token_id"]
        return _resp(book_tundra if token == "tok_tundra" else book_spirit)

    http = AsyncMock()
    http.get = AsyncMock(side_effect=fake_get)
    client = _client(http)

    snap = await client.get_market_snapshot({"Tundra"}, {"Team Spirit"})

    assert snap is not None
    # picked the Game 1 child_moneyline market, not the series one
    assert snap.market_slug == "tundra-vs-spirit-game-1"
    assert snap.condition_id == "0xabc"
    assert snap.event_slug == "blast-slam-2026"
    # side_a = radiant (Tundra), side_b = dire (Spirit)
    assert snap.side_a.token_id == "tok_tundra"
    assert snap.side_a.best_ask == 0.62
    assert snap.side_a.liquidity == 9000.0
    assert snap.side_b.token_id == "tok_spirit"
    assert snap.side_b.best_bid == 0.38


@pytest.mark.asyncio
async def test_get_market_snapshot_returns_none_when_no_game_market() -> None:
    # Only a series market exists -> no per-game market to capture -> None.
    event = {"slug": "blast-slam-2026", "markets": [_series_market()]}
    http = AsyncMock()
    http.get = AsyncMock(return_value=_resp([event]))
    client = _client(http)

    snap = await client.get_market_snapshot({"Tundra"}, {"Team Spirit"})
    assert snap is None


@pytest.mark.asyncio
async def test_get_market_snapshot_none_when_orderbook_404() -> None:
    # Market resolved between discovery and book fetch -> CLOB 404 -> clean no-market.
    event = {"slug": "blast-slam-2026", "markets": [_game1_market()]}

    async def fake_get(url, params=None):
        if url.endswith("/events"):
            return _resp([event])
        return _resp({"error": "No orderbook exists for the requested token id"}, status_code=404)

    http = AsyncMock()
    http.get = AsyncMock(side_effect=fake_get)
    client = _client(http)

    snap = await client.get_market_snapshot({"Tundra"}, {"Team Spirit"})
    assert snap is None
