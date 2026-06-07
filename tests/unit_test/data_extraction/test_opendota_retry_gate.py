"""Unit tests for the OpenDota task retry gate (don't retry 404s)."""

import aiohttp

from dota_oracle_pipeline.data_extraction.api_clients.opendota_api import retry_if_not_404


class _ReqInfo:
    real_url = "http://api.opendota.com/api/matches/1"


def _client_error(status: int) -> aiohttp.ClientResponseError:
    return aiohttp.ClientResponseError(request_info=_ReqInfo(), history=(), status=status, message="err")


class _FakeState:
    """Minimal stand-in for a Prefect terminal state."""

    def __init__(self, exc: BaseException | None):
        self._exc = exc

    def result(self, raise_on_failure: bool = True):
        if self._exc is not None and raise_on_failure:
            raise self._exc
        return "ok"


def test_404_is_not_retried():
    assert retry_if_not_404(None, None, _FakeState(_client_error(404))) is False


def test_5xx_is_retried():
    assert retry_if_not_404(None, None, _FakeState(_client_error(500))) is True


def test_429_is_retried():
    assert retry_if_not_404(None, None, _FakeState(_client_error(429))) is True


def test_other_exception_is_retried():
    assert retry_if_not_404(None, None, _FakeState(ValueError("boom"))) is True


def test_success_is_not_retried():
    assert retry_if_not_404(None, None, _FakeState(None)) is False
