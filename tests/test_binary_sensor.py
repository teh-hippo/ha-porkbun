"""Tests for the binary sensor (health status)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.porkbun_ddns.api import PorkbunApiError
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

from .conftest import MOCK_API_KEY, MOCK_DOMAIN, MOCK_SECRET_KEY


@pytest.fixture(autouse=True)
def _enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations."""


def _make_entry(hass: HomeAssistant, **options) -> MockConfigEntry:
    """Create and register a mock config entry."""
    defaults = {
        CONF_SUBDOMAINS: ["www"],
        CONF_IPV4: True,
        CONF_IPV6: False,
        CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
    }
    defaults.update(options)
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCK_DOMAIN,
        data={
            CONF_API_KEY: MOCK_API_KEY,
            CONF_SECRET_KEY: MOCK_SECRET_KEY,
            CONF_DOMAIN: MOCK_DOMAIN,
        },
        options=defaults,
    )
    entry.add_to_hass(hass)
    return entry


async def test_health_sensor_healthy(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test health sensor shows healthy (off) when all records succeed."""
    entry = _make_entry(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(f"binary_sensor.{MOCK_DOMAIN.replace('.', '_')}_dns_status")
    assert state is not None
    assert state.state == "off"  # off = no problem = healthy ✅
    assert state.attributes["summary"] == "2/2 OK"


async def test_health_sensor_partial_failure(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test health sensor shows problem when some records fail."""
    call_count = 0

    async def _get_records_with_failure(domain, record_type, subdomain=""):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise PorkbunApiError("DNS error")
        return []

    mock_porkbun_client.get_records.side_effect = _get_records_with_failure

    entry = _make_entry(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(f"binary_sensor.{MOCK_DOMAIN.replace('.', '_')}_dns_status")
    assert state is not None
    assert state.state == "on"  # on = problem detected
    assert "1/2" in state.attributes["summary"]
