"""Unit tests for sync_pro_matches batch processing (skip-present backfill)."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from dota_oracle_schedules.data_fetching import sync_pro_matches as spm

pytestmark = pytest.mark.asyncio

MOD = "dota_oracle_schedules.data_fetching.sync_pro_matches"


class _ACM:
    """Minimal async context manager yielding a fixed value."""

    def __init__(self, value):
        self._value = value

    async def __aenter__(self):
        return self._value

    async def __aexit__(self, *exc):
        return False


def _session_factory():
    """A session_factory() whose sessions support `async with session.begin()`."""

    def _make():
        session = MagicMock()
        session.begin = MagicMock(return_value=_ACM(None))
        return _ACM(session)

    return MagicMock(side_effect=lambda: _make())


async def test_process_match_batch_skips_already_stored(mocker):
    """Only matches missing from the DB (absent or outcome-less) are fetched + upserted."""
    match_ids = [101, 102, 103]
    mocker.patch(f"{MOD}.get_run_logger", return_value=MagicMock())
    # 102 already stored with an outcome -> must be skipped.
    mocker.patch(f"{MOD}.find_existing_Ids", new=AsyncMock(return_value={102}))
    fetch_mock = mocker.patch(
        f"{MOD}.fetch_completed_matches_concurrently", new=AsyncMock(return_value=["m101", "m103"])
    )
    repo = AsyncMock()
    mocker.patch(f"{MOD}.MatchRepository", return_value=repo)

    count = await spm.process_match_batch.fn(match_ids, 20, _session_factory())

    assert count == 2
    # Only the two missing ids were sent to the (paid) detail fetch.
    assert fetch_mock.await_args.args[0] == {101, 103}
    repo.upsert_match_with_outcome.assert_awaited_once_with(["m101", "m103"])


async def test_process_match_batch_all_present_makes_no_paid_calls(mocker):
    """If every match in the batch is already stored, nothing is fetched or upserted."""
    match_ids = [201, 202]
    mocker.patch(f"{MOD}.get_run_logger", return_value=MagicMock())
    mocker.patch(f"{MOD}.find_existing_Ids", new=AsyncMock(return_value={201, 202}))
    fetch_mock = mocker.patch(f"{MOD}.fetch_completed_matches_concurrently", new=AsyncMock())
    repo = AsyncMock()
    mocker.patch(f"{MOD}.MatchRepository", return_value=repo)

    count = await spm.process_match_batch.fn(match_ids, 20, _session_factory())

    assert count == 0
    fetch_mock.assert_not_awaited()
    repo.upsert_match_with_outcome.assert_not_awaited()
