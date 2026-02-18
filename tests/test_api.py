"""Tests for the Porkbun API client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from custom_components.porkbun_ddns.api import PorkbunApiError, PorkbunAuthError, PorkbunClient
from custom_components.porkbun_ddns.const import API_REQUEST_TIMEOUT

API_KEY = "pk1_test"
SECRET_KEY = "sk1_test"


BASE_RECORD = {
    "id": "123",
    "name": "example.com",
    "type": "A",
    "content": "1.2.3.4",
    "ttl": "600",
    "prio": "0",
    "notes": "",
}


def _mock_response(payload: dict, status: int = 200) -> MagicMock:
    response = MagicMock()
    response.status = status
    response.json = AsyncMock(return_value=payload)
    return response


def _make_session(response: MagicMock) -> MagicMock:
    session = MagicMock(spec=aiohttp.ClientSession)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=response)
    ctx.__aexit__ = AsyncMock(return_value=False)
    session.post.return_value = ctx
    return session


def _client(session: MagicMock) -> PorkbunClient:
    return PorkbunClient(session, API_KEY, SECRET_KEY)


async def test_ping_success() -> None:
    session = _make_session(_mock_response({"status": "SUCCESS", "yourIp": "1.2.3.4"}))
    assert await _client(session).ping() == "1.2.3.4"


async def test_ping_auth_error() -> None:
    session = _make_session(_mock_response({"status": "ERROR", "message": "Invalid API key"}))
    with pytest.raises(PorkbunAuthError, match="Invalid API key"):
        await _client(session).ping()


async def test_ping_network_error() -> None:
    session = MagicMock(spec=aiohttp.ClientSession)
    session.post.side_effect = aiohttp.ClientConnectionError("Connection refused")
    with pytest.raises(aiohttp.ClientConnectionError):
        await _client(session).ping()


@pytest.mark.parametrize(
    ("subdomain", "payload", "expected_count", "expected_name_contains"),
    [
        ("", {"status": "SUCCESS", "records": [BASE_RECORD]}, 1, "example.com"),
        (
            "www",
            {
                "status": "SUCCESS",
                "records": [{**BASE_RECORD, "id": "456", "name": "www.example.com", "content": "5.6.7.8"}],
            },
            1,
            "www.example.com",
        ),
        ("", {"status": "ERROR", "message": "No records found"}, 0, ""),
    ],
)
async def test_get_records_paths(
    subdomain: str,
    payload: dict,
    expected_count: int,
    expected_name_contains: str,
) -> None:
    session = _make_session(_mock_response(payload))
    records = await _client(session).get_records("example.com", "A", subdomain)

    assert len(records) == expected_count
    if records:
        assert expected_name_contains in records[0].name
        assert records[0].record_type == "A"


@pytest.mark.parametrize("subdomain", ["", "www"])
async def test_create_record_paths(subdomain: str) -> None:
    session = _make_session(_mock_response({"status": "SUCCESS", "id": "789"}))

    assert await _client(session).create_record("example.com", "A", "1.2.3.4", subdomain) == "789"
    payload = session.post.call_args.kwargs["json"]
    assert payload.get("name", "") == subdomain


@pytest.mark.parametrize("subdomain", ["", "www"])
async def test_edit_record_paths(subdomain: str) -> None:
    session = _make_session(_mock_response({"status": "SUCCESS"}))

    await _client(session).edit_record_by_name_type("example.com", "A", "5.6.7.8", subdomain)
    url = session.post.call_args.args[0]
    expected_suffix = "editByNameType/example.com/A" + (f"/{subdomain}" if subdomain else "")
    assert expected_suffix in url


async def test_api_error() -> None:
    session = _make_session(_mock_response({"status": "ERROR", "message": "Something went wrong"}))
    with pytest.raises(PorkbunApiError, match="Something went wrong"):
        await _client(session).create_record("example.com", "A", "1.2.3.4")


@pytest.mark.parametrize(
    ("domains", "expected_found"),
    [
        (
            [
                {
                    "domain": "example.com",
                    "status": "ACTIVE",
                    "expireDate": "2026-02-18 23:59:59",
                    "whoisPrivacy": "1",
                    "autoRenew": "1",
                }
            ],
            True,
        ),
        (
            [
                {
                    "domain": "other.com",
                    "status": "ACTIVE",
                    "expireDate": "2026-01-01 00:00:00",
                    "whoisPrivacy": "0",
                    "autoRenew": "0",
                }
            ],
            False,
        ),
    ],
)
async def test_get_domain_info(domains: list[dict[str, str]], expected_found: bool) -> None:
    session = _make_session(_mock_response({"status": "SUCCESS", "domains": domains}))
    info = await _client(session).get_domain_info("example.com")

    assert (info is not None) is expected_found
    if info:
        assert info.domain == "example.com"
        assert info.status == "ACTIVE"
        assert info.expire_date == "2026-02-18 23:59:59"
        assert info.whois_privacy is True
        assert info.auto_renew is True


async def test_request_passes_timeout() -> None:
    session = _make_session(_mock_response({"status": "SUCCESS", "yourIp": "1.2.3.4"}))
    await _client(session).ping()

    timeout = session.post.call_args.kwargs.get("timeout")
    assert isinstance(timeout, aiohttp.ClientTimeout)
    assert timeout.total == API_REQUEST_TIMEOUT


async def test_request_timeout_raises_update_failed() -> None:
    session = MagicMock(spec=aiohttp.ClientSession)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(side_effect=TimeoutError())
    ctx.__aexit__ = AsyncMock(return_value=False)
    session.post.return_value = ctx

    with pytest.raises(TimeoutError):
        await _client(session).ping()
