"""Unit tests for PublicMatchRepository.trim_to_max_rows batched-delete control flow."""

import pytest

from dota_oracle_common.repositories.public_match_repository import PublicMatchRepository

pytestmark = pytest.mark.asyncio


class _Result:
    def __init__(self, scalar=None, rowcount=0):
        self._scalar = scalar
        self.rowcount = rowcount

    def scalar_one_or_none(self):
        return self._scalar


class _FakeSession:
    """Returns queued results for successive execute() calls; counts commits."""

    def __init__(self, results):
        self._results = list(results)
        self.commits = 0
        self.executes = 0

    async def execute(self, _stmt):
        self.executes += 1
        return self._results.pop(0)

    async def commit(self):
        self.commits += 1


async def test_trim_noop_when_under_cap():
    session = _FakeSession([_Result(scalar=None)])  # OFFSET past end -> no cutoff
    repo = PublicMatchRepository(session)

    deleted = await repo.trim_to_max_rows(max_rows=500_000)

    assert deleted == 0
    assert session.commits == 0  # nothing deleted, nothing committed
    assert session.executes == 1  # only the cutoff lookup


async def test_trim_deletes_in_batches_until_drained():
    # cutoff lookup, then three delete batches: full, full, partial -> stop.
    session = _FakeSession(
        [
            _Result(scalar=8_400_000_000),
            _Result(rowcount=20_000),
            _Result(rowcount=20_000),
            _Result(rowcount=3_000),
        ]
    )
    repo = PublicMatchRepository(session)

    deleted = await repo.trim_to_max_rows(max_rows=500_000, batch_size=20_000)

    assert deleted == 43_000
    assert session.commits == 3  # one commit per delete batch
