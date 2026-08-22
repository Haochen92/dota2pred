"""Uncached OpenDota fetch swallows 404 (returns empty, no raise) so stale lookups don't
pollute Prefect with Failed task runs; other errors still propagate."""

import aiohttp
import pytest

from dota_oracle_pipeline.data_extraction.api_clients import opendota_api
from dota_oracle_pipeline.data_extraction.fetch_match_details import fetch_match_details

pytestmark = pytest.mark.asyncio


class _ReqInfo:
    real_url = "http://api.opendota.com/api/matches/1"


class _FakeResp:
    def __init__(self, status: int, payload=None):
        self.status = status
        self._payload = payload if payload is not None else {"match_id": 1}

    def raise_for_status(self):
        if self.status >= 400:
            raise aiohttp.ClientResponseError(request_info=_ReqInfo(), history=(), status=self.status, message="err")

    async def json(self):
        return self._payload


class _FakeGetCM:
    def __init__(self, resp):
        self._resp = resp

    async def __aenter__(self):
        return self._resp

    async def __aexit__(self, *exc):
        return False


class _FakeSession:
    def __init__(self, resp):
        self._resp = resp

    def get(self, *args, **kwargs):
        return _FakeGetCM(self._resp)


def _client(status: int, payload=None):
    return opendota_api.OpenDotaClient(
        session=_FakeSession(_FakeResp(status, payload)),
        api_key="dummy-key",
    )


async def test_uncached_returns_empty_on_404():
    out = await _client(404).fetch_paid_uncached(endpoint="matches/123")
    assert out == {}


async def test_uncached_raises_on_500():
    with pytest.raises(aiohttp.ClientResponseError):
        await _client(500).fetch_paid_uncached(endpoint="matches/123")


async def test_uncached_returns_payload_on_200():
    out = await _client(200, payload={"match_id": 7}).fetch_paid_uncached(endpoint="matches/7")
    assert out == {"match_id": 7}


async def test_fetch_match_details_returns_none_on_empty(mocker):
    # The 404-swallow surfaces as an empty dict; fetch_match_details must treat it as "no data".
    mocker.patch(
        "dota_oracle_pipeline.data_extraction.fetch_match_details.fetch_opendota_api_uncached",
        new=mocker.AsyncMock(return_value={}),
    )
    assert await fetch_match_details(123) is None
