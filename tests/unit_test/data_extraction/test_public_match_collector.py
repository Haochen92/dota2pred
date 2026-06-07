"""Unit tests for the incremental (frontier-bounded) public-match collector."""

import pytest

from dota_oracle_common.models.match import PublicMatch
from dota_oracle_pipeline.data_extraction import public_match_collector as pmc
from dota_oracle_pipeline.data_extraction.public_match_collector import PublicMatchCollector

pytestmark = pytest.mark.asyncio


def _pm(mid: int) -> PublicMatch:
    return PublicMatch(
        match_id=mid,
        start_time=1_700_000_000,
        duration=1800,
        avg_rank_tier=81,
        num_rank_tier=5,
        radiant_win=True,
        radiant_team=[1, 2, 3, 4, 5],
        dire_team=[6, 7, 8, 9, 10],
    )


class _FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def commit(self):
        return None


def _session_factory():
    return _FakeSession()


def _make_collector() -> PublicMatchCollector:
    return PublicMatchCollector(session_factory=_session_factory, min_rank=80, max_rank=85, insert_batch_size=1000)


def _fake_stream(matches):
    async def gen(**kwargs):
        for m in matches:
            yield m

    return gen


async def test_collect_incremental_inserts_only_above_frontier(mocker):
    """Matches newer than the frontier are inserted; the frontier match stops the loop."""
    frontier = 105
    matches = [_pm(110), _pm(108), _pm(106), _pm(105), _pm(104)]
    mocker.patch.object(pmc, "stream_public_matches", _fake_stream(matches))

    collector = _make_collector()
    inserted: list[int] = []

    async def fake_process(repo, batch, *args):
        inserted.extend(m.match_id for m in batch)
        return len(batch)

    mocker.patch.object(collector, "_process_batch", side_effect=fake_process)

    result = await collector.collect_incremental(start_match_id=9_999_999, frontier_match_id=frontier, max_pages=10)

    assert inserted == [110, 108, 106]
    assert result["total_new"] == 3


async def test_collect_incremental_no_new_when_all_below_frontier(mocker):
    """If the sample hasn't advanced past the frontier, nothing is inserted."""
    matches = [_pm(100), _pm(99)]
    mocker.patch.object(pmc, "stream_public_matches", _fake_stream(matches))

    collector = _make_collector()

    async def fake_process(repo, batch, *args):
        return len(batch)

    mock_process = mocker.patch.object(collector, "_process_batch", side_effect=fake_process)

    result = await collector.collect_incremental(start_match_id=9_999_999, frontier_match_id=105, max_pages=10)

    assert result["total_new"] == 0
    # Only the final empty-batch flush; never a populated batch.
    assert all(len(call.args[1]) == 0 for call in mock_process.call_args_list)
