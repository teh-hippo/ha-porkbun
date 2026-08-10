"""Contract tests against Porkbun's credential-free mock API."""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

import aiohttp
import pytest

from custom_components.porkbun_ddns.api import PorkbunApiError, PorkbunClient

MOCK_API_BASE = "https://api.porkbun.com/api/json/v3/mock"

pytestmark = [
    pytest.mark.contract,
    pytest.mark.enable_socket,
    pytest.mark.skipif(
        os.environ.get("PORKBUN_RUN_CONTRACT") != "1",
        reason="Porkbun contract tests are opt-in",
    ),
]


class _MockGetSession:
    """Adapt the client's POST calls to the mock server's credential-free GET API."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    def post(self, url: str, **_: Any):
        """Return an aiohttp request context manager for a GET request."""
        return self._session.get(url)


async def test_mock_success_contract_for_all_client_operations(external_network: None) -> None:
    async with aiohttp.ClientSession() as session:
        client = PorkbunClient(
            _MockGetSession(session),
            "mock-api-key",
            "mock-secret-key",
            api_base=MOCK_API_BASE,
        )

        assert await client.ping()

        records = await client.get_records("example.com", "A", "ci")
        assert records
        assert records[0].record_type == "A"
        assert records[0].content

        assert await client.create_record("example.com", "A", "192.0.2.10", "ci")
        await client.edit_record_by_name_type("example.com", "A", "198.51.100.20", "ci")
        await client.delete_records_by_name_type("example.com", "A", "ci")

        info = await client.get_domain_info("example.com")
        assert info is not None
        assert info.domain == "example.com"
        assert info.whois_privacy is True
        assert info.auto_renew is True


async def test_mock_error_contract_matches_structured_parser(external_network: None) -> None:
    async with aiohttp.ClientSession() as session:
        error: PorkbunApiError | None = None
        for attempt in range(3):
            async with session.get(f"{MOCK_API_BASE}/ping?status=error") as response:
                body = await response.text()
                if body:
                    try:
                        payload = json.loads(body)
                    except json.JSONDecodeError:
                        pass
                    else:
                        assert isinstance(payload, dict)
                        error = PorkbunClient._error_from_response(payload, response)
                        break
            if attempt < 2:
                await asyncio.sleep(attempt + 1)

        assert error is not None
        assert isinstance(error, PorkbunApiError)
        assert error.code
        assert error.http_status == 400
