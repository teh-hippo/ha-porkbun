"""Shared fixtures for Porkbun DDNS tests."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.porkbun_ddns.const import (
    CONF_API_KEY,
    CONF_DOMAIN,
    CONF_IPV4,
    CONF_IPV6,
    CONF_SECRET_KEY,
    CONF_SUBDOMAINS,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
)

MOCK_API_KEY = "pk1_test_key"
MOCK_SECRET_KEY = "sk1_test_secret"
MOCK_DOMAIN = "example.com"
MOCK_IPV4 = "1.2.3.4"
MOCK_IPV6 = "2001:db8::1"


@pytest.fixture
def mock_config_entry_data() -> dict:
    """Return mock config entry data."""
    return {
        CONF_API_KEY: MOCK_API_KEY,
        CONF_SECRET_KEY: MOCK_SECRET_KEY,
        CONF_DOMAIN: MOCK_DOMAIN,
    }


@pytest.fixture
def mock_config_entry_options() -> dict:
    """Return mock config entry options."""
    return {
        CONF_SUBDOMAINS: ["www"],
        CONF_IPV4: True,
        CONF_IPV6: False,
        CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
    }


@pytest.fixture
def mock_porkbun_client() -> Generator[AsyncMock]:
    """Mock the PorkbunClient."""
    with (
        patch(
            "custom_components.porkbun_ddns.coordinator.PorkbunClient",
            autospec=True,
        ) as mock_cls,
        patch(
            "custom_components.porkbun_ddns.coordinator.PorkbunDdnsCoordinator._get_session",
        ),
    ):
        client = mock_cls.return_value
        client.ping = AsyncMock(return_value=MOCK_IPV4)
        client.get_records = AsyncMock(return_value=[])
        client.create_record = AsyncMock(return_value="12345")
        client.edit_record_by_name_type = AsyncMock()
        client.get_domain_info = AsyncMock(return_value=None)
        yield client
