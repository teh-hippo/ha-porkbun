"""Tests for the diagnostics platform."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
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
from custom_components.porkbun_ddns.diagnostics import async_get_config_entry_diagnostics

from .conftest import MOCK_API_KEY, MOCK_DOMAIN, MOCK_SECRET_KEY


@pytest.fixture(autouse=True)
def _enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations."""


async def test_diagnostics(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test diagnostics returns expected structure with redacted keys."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCK_DOMAIN,
        data={
            CONF_API_KEY: MOCK_API_KEY,
            CONF_SECRET_KEY: MOCK_SECRET_KEY,
            CONF_DOMAIN: MOCK_DOMAIN,
        },
        options={
            CONF_SUBDOMAINS: ["www"],
            CONF_IPV4: True,
            CONF_IPV6: False,
            CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await async_get_config_entry_diagnostics(hass, entry)

    # Config keys should be redacted
    assert result["config"][CONF_API_KEY] == "**REDACTED**"
    assert result["config"][CONF_SECRET_KEY] == "**REDACTED**"
    assert result["config"][CONF_DOMAIN] == MOCK_DOMAIN

    # Options should be present
    assert result["options"][CONF_SUBDOMAINS] == ["www"]

    # Coordinator data should be present
    assert result["coordinator"]["domain"] == MOCK_DOMAIN
    assert result["coordinator"]["ipv4_enabled"] is True
    assert result["coordinator"]["record_count"] >= 1
    assert "records" in result["coordinator"]
