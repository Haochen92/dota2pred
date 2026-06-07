"""Unit tests for bounded, rate-limit-tolerant /proMatches pagination."""

import aiohttp
import pytest

from dota_oracle_pipeline.data_extraction.fetch_pro_match import fetch_pro_match

pytestmark = pytest.mark.asyncio

# Patch the free-then-paid fetch where fetch_pro_match looks it up. Mocking it directly
# exercises fetch_pro_match's pagination/429 handling; the wrapper's own free->paid fallback
# is covered in test_opendota_free_then_paid.py.
FETCH_OPENDOTA = "dota_oracle_pipeline.data_extraction.fetch_pro_match.fetch_opendota_free_then_paid"


def _page(less_than: int, n: int = 100):
    """A page of n pro matches with ids strictly descending below `less_than`."""
    return [{"match_id": less_than - i, "radiant_win": (i % 2 == 0)} for i in range(1, n + 1)]


class _ReqInfo:
    real_url = "http://api.opendota.com/api/proMatches"


def _client_error(status: int) -> aiohttp.ClientResponseError:
    return aiohttp.ClientResponseError(request_info=_ReqInfo(), history=(), status=status, message="err")


async def test_pagination_is_bounded_by_max_pages(mocker):
    """A never-reached `min` must not page forever — the cap stops it."""
    calls = {"n": 0}

    async def fake(endpoint, params=None):
        calls["n"] += 1
        return _page(params["less_than_match_id"])

    mocker.patch(FETCH_OPENDOTA, side_effect=fake)

    res = await fetch_pro_match(max_match_id=10_000_000, min_match_id=1, max_pages=3)

    assert calls["n"] == 3
    assert len(res) == 300


async def test_429_returns_partial_without_raising(mocker):
    """One 429 must degrade to partial results, not fail the whole batch."""

    async def fake(endpoint, params=None):
        if params["less_than_match_id"] == 10_000_000:
            return _page(10_000_000, n=100)  # first page OK
        raise _client_error(429)  # subsequent page rate-limited

    mocker.patch(FETCH_OPENDOTA, side_effect=fake)

    res = await fetch_pro_match(max_match_id=10_000_000, min_match_id=1, max_pages=10)

    assert len(res) == 100  # kept the first page, stopped on 429, no exception


async def test_non_429_client_error_propagates(mocker):
    async def fake(endpoint, params=None):
        raise _client_error(500)

    mocker.patch(FETCH_OPENDOTA, side_effect=fake)

    with pytest.raises(aiohttp.ClientResponseError):
        await fetch_pro_match(10_000_000, 1)


async def test_stops_naturally_when_reaching_min(mocker):
    """When a page drops below `min_match_id`, it stops before hitting the page cap."""
    calls = {"n": 0}

    async def fake(endpoint, params=None):
        calls["n"] += 1
        return _page(params["less_than_match_id"], n=100)  # ids go below min in one page

    mocker.patch(FETCH_OPENDOTA, side_effect=fake)

    res = await fetch_pro_match(max_match_id=50, min_match_id=1, max_pages=10)

    assert calls["n"] == 1
    assert len(res) == 100
