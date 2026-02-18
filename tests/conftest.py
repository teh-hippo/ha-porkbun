"""Shared fixtures for Porkbun DDNS tests."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.porkbun_ddns.const import (
    CONF_API_KEY,
    CONF_DOMAIN,
    CONF_IPV4,
    CONF_IPV6,
    CONF_SECRET_KEY,
    CONF_SUBDOMAINS,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)

MOCK_API_KEY = "pk1_test_key"
MOCK_SECRET_KEY = "sk1_test_secret"
MOCK_DOMAIN = "example.com"
MOCK_IPV4 = "1.2.3.4"
MOCK_IPV6 = "2001:db8::1"


def make_entry(hass: HomeAssistant, *, domain_name: str = MOCK_DOMAIN, **options: Any) -> MockConfigEntry:
    """Create and register a mock config entry."""
    defaults = {
        CONF_SUBDOMAINS: [],
        CONF_IPV4: True,
        CONF_IPV6: False,
        CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
    }
    defaults.update(options)
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=domain_name,
        data={
            CONF_API_KEY: MOCK_API_KEY,
            CONF_SECRET_KEY: MOCK_SECRET_KEY,
            CONF_DOMAIN: domain_name,
        },
        options=defaults,
    )
    entry.add_to_hass(hass)
    return entry


def get_entity_id(hass: HomeAssistant, platform: str, unique_id: str) -> str:
    """Look up entity_id by unique_id via entity registry."""
    ent_reg = er.async_get(hass)
    entity_id = ent_reg.async_get_entity_id(platform, DOMAIN, unique_id)
    assert entity_id is not None, f"Entity not found: {platform}.{unique_id}"
    return entity_id


@pytest.fixture
def mock_porkbun_client() -> Generator[AsyncMock]:
    """Mock the PorkbunClient."""
    with (
        patch(
            "custom_components.porkbun_ddns.coordinator.PorkbunClient",
            autospec=True,
        ) as mock_cls,
        patch(
            "custom_components.porkbun_ddns.coordinator.async_get_clientsession",
        ),
    ):
        client = mock_cls.return_value
        client.ping = AsyncMock(return_value=MOCK_IPV4)
        client.get_records = AsyncMock(return_value=[])
        client.create_record = AsyncMock(return_value="12345")
        client.edit_record_by_name_type = AsyncMock()
        client.get_domain_info = AsyncMock(return_value=None)
        yield client
