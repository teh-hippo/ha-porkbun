"""Live integration tests against Porkbun's isolated sandbox API."""

from __future__ import annotations

import os
import secrets

import aiohttp
import pytest

from custom_components.porkbun_ddns.api import PorkbunApiError, PorkbunAuthError, PorkbunClient

from .sandbox_support import ensure_sandbox_domain, sandbox_client, sandbox_credentials

pytestmark = [
    pytest.mark.sandbox,
    pytest.mark.enable_socket,
    pytest.mark.skipif(
        os.environ.get("PORKBUN_RUN_SANDBOX") != "1",
        reason="Porkbun live sandbox tests are opt-in",
    ),
]


async def test_complete_sandbox_dns_lifecycle(external_network: None) -> None:
    sandbox_credentials()
    async with aiohttp.ClientSession() as session:
        client = sandbox_client(session)
        assert await client.ping()
        ping_data = await client._request("ping")
        assert ping_data.get("sandbox") is True

        domain = await ensure_sandbox_domain(client)
        domain_info = await client.get_domain_info(domain)
        assert domain_info is not None
        assert domain_info.domain == domain

        subdomain = f"ci-{secrets.token_hex(6)}"
        created = False
        try:
            assert await client.get_records(domain, "A", subdomain) == []

            record_id = await client.create_record(domain, "A", "192.0.2.10", subdomain)
            assert record_id
            created = True

            records = await client.get_records(domain, "A", subdomain)
            assert records
            assert records[0].content == "192.0.2.10"

            await client.edit_record_by_name_type(domain, "A", "198.51.100.20", subdomain)
            records = await client.get_records(domain, "A", subdomain)
            assert records
            assert records[0].content == "198.51.100.20"
        finally:
            if created:
                await client.delete_records_by_name_type(domain, "A", subdomain)

        assert await client.get_records(domain, "A", subdomain) == []


async def test_sandbox_real_error_classification(external_network: None) -> None:
    api_key, secret_key = sandbox_credentials()
    async with aiohttp.ClientSession() as session:
        invalid_client = PorkbunClient(session, api_key, f"{secret_key}-invalid")
        with pytest.raises(PorkbunAuthError) as auth_error:
            await invalid_client.ping()
        assert auth_error.value.code in {"INVALID_API_KEYS_001", "INVALID_API_KEYS_002"}

        client = PorkbunClient(session, api_key, secret_key)
        with pytest.raises(PorkbunApiError) as domain_error:
            await client.get_records("not-a-domain.invalid", "A", "missing")
        assert not isinstance(domain_error.value, PorkbunAuthError)
        assert domain_error.value.code
