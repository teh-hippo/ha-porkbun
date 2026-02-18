"""Tests for the sensor entities."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.porkbun_ddns.api import DomainInfo
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


def _get_entity_id(hass: HomeAssistant, platform: str, unique_id: str) -> str:
    """Look up entity_id by unique_id via entity registry."""
    ent_reg = er.async_get(hass)
    entity_id = ent_reg.async_get_entity_id(platform, DOMAIN, unique_id)
    assert entity_id is not None, f"Entity not found: {platform}.{unique_id}"
    return entity_id


@pytest.fixture(autouse=True)
def _enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations."""


def _make_entry(hass: HomeAssistant, *, ipv6: bool = False, subdomains: list[str] | None = None) -> MockConfigEntry:
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
            CONF_SUBDOMAINS: subdomains or ["www"],
            CONF_IPV4: True,
            CONF_IPV6: ipv6,
            CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
        },
    )
    entry.add_to_hass(hass)
    return entry


async def test_sensors_created(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test that device-level sensors are created (3 active by default)."""
    entry = _make_entry(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    states = {s.entity_id: s for s in hass.states.async_all()}
    sensor_ids = [
        eid for eid in states if eid.startswith("sensor.") and ("porkbun" in eid.lower() or "example" in eid.lower())
    ]
    # IP + domain expiry sensors are disabled by default.
    assert len(sensor_ids) == 3, f"Expected 3 sensors, got {len(sensor_ids)}: {sensor_ids}"


async def test_managed_subdomains_sensor_value_and_attributes(
    hass: HomeAssistant, mock_porkbun_client: AsyncMock
) -> None:
    """Test managed subdomains sensor shows root + configured subdomains."""
    entry = _make_entry(hass, subdomains=["www", "vpn"])

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(_get_entity_id(hass, "sensor", f"{MOCK_DOMAIN}_managed_subdomains"))
    assert state is not None
    assert state.state == "@, www, vpn"
    assert state.attributes["managed_records"] == [
        MOCK_DOMAIN,
        f"www.{MOCK_DOMAIN}",
        f"vpn.{MOCK_DOMAIN}",
    ]


async def test_managed_subdomains_sensor_updates_after_reload(
    hass: HomeAssistant, mock_porkbun_client: AsyncMock
) -> None:
    """Test managed subdomains sensor reflects updated options after reload."""
    entry = _make_entry(hass, subdomains=["www"])

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity_id = _get_entity_id(hass, "sensor", f"{MOCK_DOMAIN}_managed_subdomains")
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "@, www"

    hass.config_entries.async_update_entry(
        entry,
        options={**entry.options, CONF_SUBDOMAINS: ["www", "vpn"]},
    )
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    updated_state = hass.states.get(entity_id)
    assert updated_state is not None
    assert updated_state.state == "@, www, vpn"


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


async def test_last_updated_sensor_value(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test that the last updated sensor returns the coordinator's timestamp."""
    entry = _make_entry(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(_get_entity_id(hass, "sensor", f"{MOCK_DOMAIN}_last_updated"))
    assert state is not None
    # Should be a valid ISO timestamp
    assert state.state != "unknown"
    assert state.state != "unavailable"


async def test_next_update_sensor_value(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test that the next update sensor returns last_updated + interval."""
    entry = _make_entry(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(_get_entity_id(hass, "sensor", f"{MOCK_DOMAIN}_next_update"))
    assert state is not None
    assert state.state != "unknown"
    assert state.state != "unavailable"


async def test_next_update_sensor_refreshing_when_overdue(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test that the next update sensor stays a timestamp even when overdue."""
    from datetime import timedelta

    entry = _make_entry(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    coordinator = entry.runtime_data
    coordinator.data.last_updated = coordinator.data.last_updated - timedelta(hours=1)
    coordinator.async_set_updated_data(coordinator.data)
    await hass.async_block_till_done()

    state = hass.states.get(_get_entity_id(hass, "sensor", f"{MOCK_DOMAIN}_next_update"))
    assert state is not None
    assert state.state not in {"unknown", "unavailable", "Refreshing"}


async def test_domain_expiry_sensor_value(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test domain expiry sensor returns parsed datetime when enabled."""
    mock_porkbun_client.get_domain_info.return_value = DomainInfo(
        domain=MOCK_DOMAIN,
        status="ACTIVE",
        expire_date="2026-02-18 23:59:59",
        whois_privacy=True,
        auto_renew=True,
    )
    entry = _make_entry(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    expiry_id = _get_entity_id(hass, "sensor", f"{MOCK_DOMAIN}_domain_expiry")
    ent_reg.async_update_entity(expiry_id, disabled_by=None)
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(expiry_id)
    assert state is not None
    assert state.state != "unavailable"


async def test_domain_expiry_sensor_invalid_date(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test domain expiry sensor handles invalid date gracefully."""
    mock_porkbun_client.get_domain_info.return_value = DomainInfo(
        domain=MOCK_DOMAIN,
        status="ACTIVE",
        expire_date="not-a-date",
        whois_privacy=True,
        auto_renew=True,
    )
    entry = _make_entry(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    expiry_id = _get_entity_id(hass, "sensor", f"{MOCK_DOMAIN}_domain_expiry")
    ent_reg.async_update_entity(expiry_id, disabled_by=None)
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(expiry_id)
    # Should not crash, just return None/unknown
    assert state is not None
