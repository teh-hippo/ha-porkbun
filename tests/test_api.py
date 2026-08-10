"""Tests for the Porkbun API client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

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


def _mock_response(
    payload: dict,
    status: int = 200,
    *,
    headers: dict[str, str] | None = None,
) -> MagicMock:
    response = MagicMock()
    response.status = status
    response.headers = headers or {}
    response.json = AsyncMock(return_value=payload)
    return response


def _mock_raw_response(
    json_value: object = None,
    status: int = 200,
    *,
    json_error: Exception | None = None,
    text: str = "",
    headers: dict[str, str] | None = None,
) -> MagicMock:
    response = MagicMock()
    response.status = status
    response.headers = headers or {}
    response.json = AsyncMock(side_effect=json_error) if json_error else AsyncMock(return_value=json_value)
    response.text = AsyncMock(return_value=text)
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


@pytest.mark.parametrize("code", ["INVALID_API_KEYS_001", "INVALID_API_KEYS_002"])
async def test_ping_auth_error(code: str) -> None:
    session = _make_session(
        _mock_response(
            {
                "status": "ERROR",
                "code": code,
                "message": "Invalid API key",
                "requestId": "request-auth",
            }
        )
    )
    with pytest.raises(PorkbunAuthError, match="Invalid API key") as exc_info:
        await _client(session).ping()
    assert exc_info.value.code == code
    assert exc_info.value.request_id == "request-auth"


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


async def test_invalid_domain_is_not_auth_error() -> None:
    session = _make_session(
        _mock_response(
            {
                "status": "ERROR",
                "code": "INVALID_DOMAIN",
                "message": "Invalid domain",
                "next_action": {
                    "type": "correct_input",
                    "hint": "Use a domain in the account",
                    "retryable": False,
                },
            },
            status=400,
            headers={"X-Request-Id": "request-domain"},
        )
    )

    with pytest.raises(PorkbunApiError, match="Invalid domain") as exc_info:
        await _client(session).get_records("not-a-domain", "A")

    assert not isinstance(exc_info.value, PorkbunAuthError)
    assert exc_info.value.code == "INVALID_DOMAIN"
    assert exc_info.value.http_status == 400
    assert exc_info.value.request_id == "request-domain"
    assert exc_info.value.next_action == {
        "type": "correct_input",
        "hint": "Use a domain in the account",
        "retryable": False,
    }
    assert exc_info.value.retryable is False


async def test_get_records_returns_empty_for_stable_error_code() -> None:
    session = _make_session(
        _mock_response(
            {
                "status": "ERROR",
                "code": "NO_RECORDS_FOUND",
                "message": "Nothing matched",
            }
        )
    )

    assert await _client(session).get_records("example.com", "A", "missing") == []


@pytest.mark.parametrize(
    ("domains", "expected_found"),
    [
        (
            [
                {
                    "domain": "example.com",
                    "status": "ACTIVE",
                    "expireDate": "2026-02-18 23:59:59",
                    "whoisPrivacy": 1,
                    "autoRenew": True,
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


async def test_request_retries_on_connection_error_then_succeeds() -> None:
    response = _mock_response({"status": "SUCCESS", "yourIp": "1.2.3.4"})
    success_ctx = MagicMock()
    success_ctx.__aenter__ = AsyncMock(return_value=response)
    success_ctx.__aexit__ = AsyncMock(return_value=False)

    session = MagicMock(spec=aiohttp.ClientSession)
    session.post.side_effect = [
        aiohttp.ClientConnectionError("Connection reset"),
        aiohttp.ClientConnectionError("Connection reset"),
        success_ctx,
    ]

    with (
        patch("custom_components.porkbun_ddns.api.asyncio.sleep", new=AsyncMock()) as sleep_mock,
        patch("custom_components.porkbun_ddns.api.secrets.randbelow", return_value=0),
    ):
        assert await _client(session).ping() == "1.2.3.4"

    assert session.post.call_count == 3
    assert sleep_mock.await_count == 2


async def test_request_retries_on_http_503_then_succeeds() -> None:
    error_response = _mock_response({"status": "ERROR", "message": "Service temporarily unavailable"}, status=503)
    error_ctx = MagicMock()
    error_ctx.__aenter__ = AsyncMock(return_value=error_response)
    error_ctx.__aexit__ = AsyncMock(return_value=False)

    success_response = _mock_response({"status": "SUCCESS", "yourIp": "1.2.3.4"})
    success_ctx = MagicMock()
    success_ctx.__aenter__ = AsyncMock(return_value=success_response)
    success_ctx.__aexit__ = AsyncMock(return_value=False)

    session = MagicMock(spec=aiohttp.ClientSession)
    session.post.side_effect = [error_ctx, success_ctx]

    with (
        patch("custom_components.porkbun_ddns.api.asyncio.sleep", new=AsyncMock()) as sleep_mock,
        patch("custom_components.porkbun_ddns.api.secrets.randbelow", return_value=0),
    ):
        assert await _client(session).ping() == "1.2.3.4"

    assert session.post.call_count == 2
    assert sleep_mock.await_count == 1


async def test_request_uses_retry_after_and_next_action() -> None:
    error_response = _mock_response(
        {
            "status": "ERROR",
            "code": "RATE_LIMIT_EXCEEDED",
            "message": "Slow down",
            "next_action": {"type": "wait", "retryable": True},
        },
        status=429,
        headers={"Retry-After": "7"},
    )
    error_ctx = MagicMock()
    error_ctx.__aenter__ = AsyncMock(return_value=error_response)
    error_ctx.__aexit__ = AsyncMock(return_value=False)

    success_response = _mock_response({"status": "SUCCESS", "yourIp": "1.2.3.4"})
    success_ctx = MagicMock()
    success_ctx.__aenter__ = AsyncMock(return_value=success_response)
    success_ctx.__aexit__ = AsyncMock(return_value=False)

    session = MagicMock(spec=aiohttp.ClientSession)
    session.post.side_effect = [error_ctx, success_ctx]

    with patch("custom_components.porkbun_ddns.api.asyncio.sleep", new=AsyncMock()) as sleep_mock:
        assert await _client(session).ping() == "1.2.3.4"

    sleep_mock.assert_awaited_once_with(7.0)


async def test_request_timeout_raises_after_retries() -> None:
    session = MagicMock(spec=aiohttp.ClientSession)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(side_effect=TimeoutError())
    ctx.__aexit__ = AsyncMock(return_value=False)
    session.post.return_value = ctx

    with (
        patch("custom_components.porkbun_ddns.api.asyncio.sleep", new=AsyncMock()) as sleep_mock,
        patch("custom_components.porkbun_ddns.api.secrets.randbelow", return_value=0),
    ):
        with pytest.raises(TimeoutError):
            await _client(session).ping()

    assert session.post.call_count == 3
    assert sleep_mock.await_count == 2


async def test_create_reuses_idempotency_key_across_retries() -> None:
    response = _mock_response({"status": "SUCCESS", "id": "789"})
    success_ctx = MagicMock()
    success_ctx.__aenter__ = AsyncMock(return_value=response)
    success_ctx.__aexit__ = AsyncMock(return_value=False)

    session = MagicMock(spec=aiohttp.ClientSession)
    session.post.side_effect = [aiohttp.ClientConnectionError("Connection reset"), success_ctx]

    with (
        patch("custom_components.porkbun_ddns.api.asyncio.sleep", new=AsyncMock()),
        patch("custom_components.porkbun_ddns.api.secrets.randbelow", return_value=0),
        patch("custom_components.porkbun_ddns.api.secrets.token_hex", return_value="stable-key"),
    ):
        assert await _client(session).create_record("example.com", "A", "1.2.3.4") == "789"

    assert [call.kwargs["headers"] for call in session.post.call_args_list] == [
        {"Idempotency-Key": "stable-key"},
        {"Idempotency-Key": "stable-key"},
    ]


async def test_writes_use_unique_idempotency_keys() -> None:
    session = _make_session(_mock_response({"status": "SUCCESS", "id": "789"}))

    with patch(
        "custom_components.porkbun_ddns.api.secrets.token_hex",
        side_effect=["create-key", "edit-key", "delete-key"],
    ):
        client = _client(session)
        await client.create_record("example.com", "A", "1.2.3.4", "ci")
        await client.edit_record_by_name_type("example.com", "A", "5.6.7.8", "ci")
        await client.delete_records_by_name_type("example.com", "A", "ci")

    calls = session.post.call_args_list
    assert calls[0].kwargs["headers"] == {"Idempotency-Key": "create-key"}
    assert calls[1].kwargs["headers"] == {"Idempotency-Key": "edit-key"}
    assert calls[2].kwargs["headers"] == {"Idempotency-Key": "delete-key"}
    assert calls[2].args[0].endswith("dns/deleteByNameType/example.com/A/ci")


@pytest.mark.parametrize(
    ("json_value", "text"),
    [
        (None, "null"),
        (None, ""),
        ([{"status": "SUCCESS"}], '[{"status": "SUCCESS"}]'),
        ("SUCCESS", '"SUCCESS"'),
    ],
)
async def test_request_raises_on_non_dict_body(json_value: object, text: str) -> None:
    session = _make_session(_mock_raw_response(json_value, text=text))
    with pytest.raises(PorkbunApiError, match="Invalid API response"):
        await _client(session).ping()
    assert session.post.call_count == 1


async def test_request_raises_on_invalid_json_body() -> None:
    session = _make_session(_mock_raw_response(json_error=ValueError("no json"), text="<html>502</html>"))
    with pytest.raises(PorkbunApiError, match="Invalid API response"):
        await _client(session).ping()
    assert session.post.call_count == 1


async def test_request_retries_on_null_body_5xx_then_succeeds() -> None:
    null_ctx = MagicMock()
    null_ctx.__aenter__ = AsyncMock(return_value=_mock_raw_response(None, status=503, text=""))
    null_ctx.__aexit__ = AsyncMock(return_value=False)

    success_ctx = MagicMock()
    success_ctx.__aenter__ = AsyncMock(return_value=_mock_response({"status": "SUCCESS", "yourIp": "1.2.3.4"}))
    success_ctx.__aexit__ = AsyncMock(return_value=False)

    session = MagicMock(spec=aiohttp.ClientSession)
    session.post.side_effect = [null_ctx, success_ctx]

    with (
        patch("custom_components.porkbun_ddns.api.asyncio.sleep", new=AsyncMock()) as sleep_mock,
        patch("custom_components.porkbun_ddns.api.secrets.randbelow", return_value=0),
    ):
        assert await _client(session).ping() == "1.2.3.4"

    assert session.post.call_count == 2
    assert sleep_mock.await_count == 1
