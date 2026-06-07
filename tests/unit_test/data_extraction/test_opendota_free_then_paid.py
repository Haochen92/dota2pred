"""Unit tests for the free-first / paid-fallback OpenDota fetch wrapper."""

import aiohttp
import pytest

from dota_oracle_pipeline.data_extraction.api_clients.opendota_api import fetch_opendota_free_then_paid

pytestmark = pytest.mark.asyncio

MOD = "dota_oracle_pipeline.data_extraction.api_clients.opendota_api"


class _ReqInfo:
    real_url = "http://api.opendota.com/api/proMatches"


def _client_error(status: int) -> aiohttp.ClientResponseError:
    return aiohttp.ClientResponseError(request_info=_ReqInfo(), history=(), status=status, message="err")


async def test_returns_free_result_without_touching_paid(mocker):
    mocker.patch(f"{MOD}.fetch_opendota", new=mocker.AsyncMock(return_value={"ok": "free"}))
    paid = mocker.patch(f"{MOD}.fetch_opendota_api", new=mocker.AsyncMock())

    res = await fetch_opendota_free_then_paid("proMatches")

    assert res == {"ok": "free"}
    paid.assert_not_awaited()


async def test_falls_back_to_paid_on_429(mocker):
    mocker.patch(f"{MOD}.fetch_opendota", new=mocker.AsyncMock(side_effect=_client_error(429)))
    paid = mocker.patch(f"{MOD}.fetch_opendota_api", new=mocker.AsyncMock(return_value={"ok": "paid"}))

    res = await fetch_opendota_free_then_paid("proMatches", {"less_than_match_id": 5})

    assert res == {"ok": "paid"}
    paid.assert_awaited_once_with("proMatches", {"less_than_match_id": 5})


async def test_non_429_propagates_without_paid(mocker):
    mocker.patch(f"{MOD}.fetch_opendota", new=mocker.AsyncMock(side_effect=_client_error(500)))
    paid = mocker.patch(f"{MOD}.fetch_opendota_api", new=mocker.AsyncMock())

    with pytest.raises(aiohttp.ClientResponseError):
        await fetch_opendota_free_then_paid("proMatches")

    paid.assert_not_awaited()
