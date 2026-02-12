"""Tests for the sensor entities."""

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

from .conftest import MOCK_API_KEY, MOCK_DOMAIN, MOCK_IPV4, MOCK_SECRET_KEY


@pytest.fixture(autouse=True)
def _enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations."""


def _make_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create and register a mock config entry."""
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
    return entry


async def test_sensors_created(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test that device-level sensors are created (3: IP, last updated, next update)."""
    entry = _make_entry(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    states = {s.entity_id: s for s in hass.states.async_all()}
    sensor_ids = [eid for eid in states if "porkbun" in eid.lower() or "example" in eid.lower()]
    # Should have exactly 3: Public IPv4, Last Updated, Next Update
    assert len(sensor_ids) == 3, f"Expected 3 sensors, got {len(sensor_ids)}: {sensor_ids}"


async def test_sensor_shows_ip(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test that the single IP sensor shows the correct address."""
    entry = _make_entry(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    states = {s.entity_id: s for s in hass.states.async_all()}
    ip_sensors = [s for eid, s in states.items() if "ipv4" in eid.lower() or "public" in eid.lower()]
    assert len(ip_sensors) == 1, f"Expected 1 IP sensor, got {len(ip_sensors)}"
    assert ip_sensors[0].state == MOCK_IPV4

    # Check managed_records attribute includes root + subdomain
    attrs = ip_sensors[0].attributes
    assert "managed_records" in attrs
    assert MOCK_DOMAIN in attrs["managed_records"]
    assert f"www.{MOCK_DOMAIN}" in attrs["managed_records"]
