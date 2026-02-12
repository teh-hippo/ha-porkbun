"""Tests for the Porkbun API client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from custom_components.porkbun_ddns.api import (
    PorkbunApiError,
    PorkbunAuthError,
    PorkbunClient,
)

API_KEY = "pk1_test"
SECRET_KEY = "sk1_test"


def _mock_response(payload: dict, status: int = 200) -> MagicMock:
    """Create a mock aiohttp response."""
    resp = MagicMock()
    resp.status = status
    resp.json = AsyncMock(return_value=payload)
    return resp


def _make_session(response: MagicMock) -> MagicMock:
    """Create a mock aiohttp session that returns response from post()."""
    session = MagicMock(spec=aiohttp.ClientSession)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=response)
    ctx.__aexit__ = AsyncMock(return_value=False)
    session.post.return_value = ctx
    return session


def _client(session: MagicMock) -> PorkbunClient:
    return PorkbunClient(session, API_KEY, SECRET_KEY)


async def test_ping_success() -> None:
    """Test successful ping returns IP."""
    resp = _mock_response({"status": "SUCCESS", "yourIp": "1.2.3.4"})
    session = _make_session(resp)
    ip = await _client(session).ping()
    assert ip == "1.2.3.4"


async def test_ping_auth_error() -> None:
    """Test ping with invalid credentials raises PorkbunAuthError."""
    resp = _mock_response({"status": "ERROR", "message": "Invalid API key"})
    session = _make_session(resp)
    with pytest.raises(PorkbunAuthError, match="Invalid API key"):
        await _client(session).ping()


async def test_ping_network_error() -> None:
    """Test ping with network error raises ClientError."""
    session = MagicMock(spec=aiohttp.ClientSession)
    session.post.side_effect = aiohttp.ClientConnectionError("Connection refused")
    with pytest.raises(aiohttp.ClientConnectionError):
        await _client(session).ping()


async def test_get_records_success() -> None:
    """Test retrieving DNS records."""
    resp = _mock_response(
        {
            "status": "SUCCESS",
            "records": [
                {
                    "id": "123",
                    "name": "example.com",
                    "type": "A",
                    "content": "1.2.3.4",
                    "ttl": "600",
                    "prio": "0",
                    "notes": "",
                }
            ],
        }
    )
    session = _make_session(resp)
    records = await _client(session).get_records("example.com", "A")
    assert len(records) == 1
    assert records[0].content == "1.2.3.4"
    assert records[0].record_type == "A"


async def test_get_records_with_subdomain() -> None:
    """Test retrieving DNS records for a subdomain."""
    resp = _mock_response(
        {
            "status": "SUCCESS",
            "records": [
                {
                    "id": "456",
                    "name": "www.example.com",
                    "type": "A",
                    "content": "5.6.7.8",
                    "ttl": "600",
                    "prio": "0",
                    "notes": "",
                }
            ],
        }
    )
    session = _make_session(resp)
    records = await _client(session).get_records("example.com", "A", "www")
    assert len(records) == 1
    assert records[0].name == "www.example.com"
    call_url = session.post.call_args[0][0]
    assert "/www" in call_url


async def test_get_records_empty() -> None:
    """Test retrieving records when none exist returns empty list."""
    resp = _mock_response({"status": "ERROR", "message": "No records found"})
    session = _make_session(resp)
    records = await _client(session).get_records("example.com", "A")
    assert records == []


async def test_create_record() -> None:
    """Test creating a DNS record."""
    resp = _mock_response({"status": "SUCCESS", "id": "789"})
    session = _make_session(resp)
    record_id = await _client(session).create_record("example.com", "A", "1.2.3.4")
    assert record_id == "789"


async def test_create_record_with_subdomain() -> None:
    """Test creating a DNS record for a subdomain."""
    resp = _mock_response({"status": "SUCCESS", "id": "790"})
    session = _make_session(resp)
    record_id = await _client(session).create_record("example.com", "A", "1.2.3.4", "www")
    assert record_id == "790"
    call_kwargs = session.post.call_args[1]
    assert call_kwargs["json"]["name"] == "www"


async def test_edit_record_by_name_type() -> None:
    """Test editing a DNS record by name and type."""
    resp = _mock_response({"status": "SUCCESS"})
    session = _make_session(resp)
    await _client(session).edit_record_by_name_type("example.com", "A", "5.6.7.8")
    call_url = session.post.call_args[0][0]
    assert "editByNameType/example.com/A" in call_url


async def test_edit_record_with_subdomain() -> None:
    """Test editing a DNS record for a subdomain."""
    resp = _mock_response({"status": "SUCCESS"})
    session = _make_session(resp)
    await _client(session).edit_record_by_name_type("example.com", "A", "5.6.7.8", "www")
    call_url = session.post.call_args[0][0]
    assert "editByNameType/example.com/A/www" in call_url


async def test_api_error() -> None:
    """Test generic API error raises PorkbunApiError."""
    resp = _mock_response({"status": "ERROR", "message": "Something went wrong"})
    session = _make_session(resp)
    with pytest.raises(PorkbunApiError, match="Something went wrong"):
        await _client(session).create_record("example.com", "A", "1.2.3.4")
