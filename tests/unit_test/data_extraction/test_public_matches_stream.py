"""Unit tests for the bounded, frontier-friendly /publicMatches stream."""

import pytest

from dota_oracle_common.models.match import PublicMatch
from dota_oracle_pipeline.data_extraction import public_matches_stream as pms
from dota_oracle_pipeline.data_extraction.public_matches_stream import (
    fetch_public_matches_page,
    stream_public_matches,
)

pytestmark = pytest.mark.asyncio


def _pm(mid: int, rank: int = 81) -> PublicMatch:
    return PublicMatch(
        match_id=mid,
        start_time=1_700_000_000,
        duration=1800,
        avg_rank_tier=rank,
        num_rank_tier=5,
        radiant_win=True,
        radiant_team=[1, 2, 3, 4, 5],
        dire_team=[6, 7, 8, 9, 10],
    )


def _page(less_than: int, n: int = 100, rank: int = 81):
    """A descending page of n matches below `less_than`."""
    return [_pm(less_than - i, rank) for i in range(1, n + 1)]


async def _drain(gen):
    return [m async for m in gen]


async def test_max_pages_caps_fetches(mocker):
    """A never-emptying feed must stop at the page cap, not run forever."""
    calls = {"n": 0}

    def fake_page(*, less_than_match_id, min_rank, max_rank, use_paid=True):
        calls["n"] += 1
        return _page(less_than_match_id)

    mocker.patch.object(pms, "fetch_public_matches_page", side_effect=fake_page)

    out = await _drain(
        stream_public_matches(
            start_less_than_match_id=10_000_000, min_rank=80, max_rank=85, max_pages=3, stop_on_empty=True
        )
    )

    assert calls["n"] == 3
    assert len(out) == 300


async def test_stop_on_empty_breaks_without_hopping(mocker):
    """An empty page ends the stream instead of hopping back through unfetchable history."""
    calls = {"n": 0}

    def fake_page(*, less_than_match_id, min_rank, max_rank, use_paid=True):
        calls["n"] += 1
        return _page(10_000_000, n=50) if calls["n"] == 1 else []

    mocker.patch.object(pms, "fetch_public_matches_page", side_effect=fake_page)

    out = await _drain(
        stream_public_matches(
            start_less_than_match_id=10_000_000, min_rank=80, max_rank=85, max_pages=100, stop_on_empty=True
        )
    )

    assert calls["n"] == 2  # one data page, one empty -> stop (no 40k-id hop crawl)
    assert len(out) == 50


async def test_stops_at_frontier(mocker):
    """Once the cursor crosses the frontier, no further pages are fetched."""
    calls = {"n": 0}

    def fake_page(*, less_than_match_id, min_rank, max_rank, use_paid=True):
        calls["n"] += 1
        return _page(less_than_match_id, n=100)

    mocker.patch.object(pms, "fetch_public_matches_page", side_effect=fake_page)

    # First page yields 999..900; min 900 <= frontier 950 -> next loop stops at boundary.
    await _drain(
        stream_public_matches(
            start_less_than_match_id=1000,
            min_rank=80,
            max_rank=85,
            stop_at_match_id=950,
            max_pages=100,
            stop_on_empty=True,
        )
    )

    assert calls["n"] == 1


async def test_out_of_band_matches_are_filtered(mocker):
    def fake_page(*, less_than_match_id, min_rank, max_rank, use_paid=True):
        return _page(10_000_000, n=10, rank=70)  # below the 80-85 band

    mocker.patch.object(pms, "fetch_public_matches_page", side_effect=fake_page)

    out = await _drain(
        stream_public_matches(
            start_less_than_match_id=10_000_000, min_rank=80, max_rank=85, max_pages=1, stop_on_empty=True
        )
    )

    assert out == []


async def test_use_paid_false_uses_free_endpoint(mocker):
    # fetch_opendota_api_uncached is a Prefect @task object, so patch with an explicit
    # AsyncMock rather than relying on coroutine auto-detection.
    free = mocker.patch.object(pms, "fetch_opendota", new=mocker.AsyncMock(return_value=[]))
    paid = mocker.patch.object(pms, "fetch_opendota_api_uncached", new=mocker.AsyncMock(return_value=[]))

    await fetch_public_matches_page(less_than_match_id=123, min_rank=80, max_rank=85, use_paid=False)

    free.assert_awaited_once()
    paid.assert_not_called()


async def test_use_paid_true_uses_paid_endpoint(mocker):
    free = mocker.patch.object(pms, "fetch_opendota", new=mocker.AsyncMock(return_value=[]))
    paid = mocker.patch.object(pms, "fetch_opendota_api_uncached", new=mocker.AsyncMock(return_value=[]))

    await fetch_public_matches_page(less_than_match_id=123, min_rank=80, max_rank=85, use_paid=True)

    paid.assert_awaited_once()
    free.assert_not_called()
