"""Tests for the sensor entities."""

from __future__ import annotations

from unittest.mock import AsyncMock

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

from .conftest import MOCK_API_KEY, MOCK_DOMAIN, MOCK_SECRET_KEY


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
    """Test that device-level sensors are created (2 active: last updated, next update)."""
    entry = _make_entry(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    states = {s.entity_id: s for s in hass.states.async_all()}
    sensor_ids = [
        eid for eid in states if eid.startswith("sensor.") and ("porkbun" in eid.lower() or "example" in eid.lower())
    ]
    # IP sensor is disabled by default, so only Last Updated + Next Update are active
    assert len(sensor_ids) == 2, f"Expected 2 sensors, got {len(sensor_ids)}: {sensor_ids}"


async def test_ip_sensor_disabled_by_default(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test that the IP sensor is registered but disabled by default."""
    entry = _make_entry(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    ip_entity = ent_reg.async_get_entity_id("sensor", DOMAIN, f"{MOCK_DOMAIN}_A_ip")
    assert ip_entity is not None
    entity_entry = ent_reg.async_get(ip_entity)
    assert entity_entry is not None
    assert entity_entry.disabled_by is not None


async def test_domain_expiry_sensor_disabled_by_default(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test that the domain expiry sensor is registered but disabled by default."""
    entry = _make_entry(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    expiry_entity = ent_reg.async_get_entity_id("sensor", DOMAIN, f"{MOCK_DOMAIN}_domain_expiry")
    assert expiry_entity is not None
    entity_entry = ent_reg.async_get(expiry_entity)
    assert entity_entry is not None
    assert entity_entry.disabled_by is not None
