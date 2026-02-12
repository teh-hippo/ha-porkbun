"""Tests for the Porkbun API client."""

from __future__ import annotations

import aiohttp
import pytest
from aioresponses import aioresponses

from custom_components.porkbun_ddns.api import (
    PorkbunApiError,
    PorkbunAuthError,
    PorkbunClient,
)
from custom_components.porkbun_ddns.const import PORKBUN_API_BASE

API_KEY = "pk1_test"
SECRET_KEY = "sk1_test"


@pytest.fixture
def mock_api():
    """Create aioresponses context."""
    with aioresponses() as m:
        yield m


@pytest.fixture
async def client(mock_api: aioresponses) -> PorkbunClient:
    """Create a PorkbunClient with a shared session."""
    connector = aiohttp.TCPConnector(enable_cleanup_closed=True)
    session = aiohttp.ClientSession(connector=connector)
    c = PorkbunClient(session, API_KEY, SECRET_KEY)
    yield c
    await session.close()
    await connector.close()


async def test_ping_success(mock_api: aioresponses, client: PorkbunClient) -> None:
    """Test successful ping returns IP."""
    mock_api.post(
        f"{PORKBUN_API_BASE}/ping",
        payload={"status": "SUCCESS", "yourIp": "1.2.3.4"},
    )
    ip = await client.ping()
    assert ip == "1.2.3.4"


async def test_ping_auth_error(mock_api: aioresponses, client: PorkbunClient) -> None:
    """Test ping with invalid credentials raises PorkbunAuthError."""
    mock_api.post(
        f"{PORKBUN_API_BASE}/ping",
        payload={"status": "ERROR", "message": "Invalid API key"},
    )
    with pytest.raises(PorkbunAuthError, match="Invalid API key"):
        await client.ping()


async def test_ping_network_error(mock_api: aioresponses, client: PorkbunClient) -> None:
    """Test ping with network error raises ClientError."""
    mock_api.post(
        f"{PORKBUN_API_BASE}/ping",
        exception=aiohttp.ClientConnectionError("Connection refused"),
    )
    with pytest.raises(aiohttp.ClientConnectionError):
        await client.ping()


async def test_get_records_success(mock_api: aioresponses, client: PorkbunClient) -> None:
    """Test retrieving DNS records."""
    mock_api.post(
        f"{PORKBUN_API_BASE}/dns/retrieveByNameType/example.com/A",
        payload={
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
        },
    )
    records = await client.get_records("example.com", "A")
    assert len(records) == 1
    assert records[0].content == "1.2.3.4"
    assert records[0].record_type == "A"


async def test_get_records_with_subdomain(mock_api: aioresponses, client: PorkbunClient) -> None:
    """Test retrieving DNS records for a subdomain."""
    mock_api.post(
        f"{PORKBUN_API_BASE}/dns/retrieveByNameType/example.com/A/www",
        payload={
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
        },
    )
    records = await client.get_records("example.com", "A", "www")
    assert len(records) == 1
    assert records[0].name == "www.example.com"


async def test_get_records_empty(mock_api: aioresponses, client: PorkbunClient) -> None:
    """Test retrieving records when none exist returns empty list."""
    mock_api.post(
        f"{PORKBUN_API_BASE}/dns/retrieveByNameType/example.com/A",
        payload={"status": "ERROR", "message": "No records found"},
    )
    records = await client.get_records("example.com", "A")
    assert records == []


async def test_create_record(mock_api: aioresponses, client: PorkbunClient) -> None:
    """Test creating a DNS record."""
    mock_api.post(
        f"{PORKBUN_API_BASE}/dns/create/example.com",
        payload={"status": "SUCCESS", "id": "789"},
    )
    record_id = await client.create_record("example.com", "A", "1.2.3.4")
    assert record_id == "789"


async def test_create_record_with_subdomain(mock_api: aioresponses, client: PorkbunClient) -> None:
    """Test creating a DNS record for a subdomain."""
    mock_api.post(
        f"{PORKBUN_API_BASE}/dns/create/example.com",
        payload={"status": "SUCCESS", "id": "790"},
    )
    record_id = await client.create_record("example.com", "A", "1.2.3.4", "www")
    assert record_id == "790"


async def test_edit_record_by_name_type(mock_api: aioresponses, client: PorkbunClient) -> None:
    """Test editing a DNS record by name and type."""
    mock_api.post(
        f"{PORKBUN_API_BASE}/dns/editByNameType/example.com/A",
        payload={"status": "SUCCESS"},
    )
    await client.edit_record_by_name_type("example.com", "A", "5.6.7.8")


async def test_edit_record_with_subdomain(mock_api: aioresponses, client: PorkbunClient) -> None:
    """Test editing a DNS record for a subdomain."""
    mock_api.post(
        f"{PORKBUN_API_BASE}/dns/editByNameType/example.com/A/www",
        payload={"status": "SUCCESS"},
    )
    await client.edit_record_by_name_type("example.com", "A", "5.6.7.8", "www")


async def test_api_error(mock_api: aioresponses, client: PorkbunClient) -> None:
    """Test generic API error raises PorkbunApiError."""
    mock_api.post(
        f"{PORKBUN_API_BASE}/dns/create/example.com",
        payload={"status": "ERROR", "message": "Something went wrong"},
    )
    with pytest.raises(PorkbunApiError, match="Something went wrong"):
        await client.create_record("example.com", "A", "1.2.3.4")
