"""Tests for the binary sensor (health status)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
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


def _get_entity_id(hass: HomeAssistant, platform: str, unique_id: str) -> str:
    """Look up entity_id by unique_id via entity registry."""
    ent_reg = er.async_get(hass)
    entity_id = ent_reg.async_get_entity_id(platform, DOMAIN, unique_id)
    assert entity_id is not None, f"Entity not found: {platform}.{unique_id}"
    return entity_id


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

    state = hass.states.get(_get_entity_id(hass, "binary_sensor", f"{MOCK_DOMAIN}_health"))
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

    state = hass.states.get(_get_entity_id(hass, "binary_sensor", f"{MOCK_DOMAIN}_health"))
    assert state is not None
    assert state.state == "on"  # on = problem detected
    assert "1/2" in state.attributes["summary"]


async def test_whois_privacy_sensor_disabled_by_default(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test WHOIS privacy sensor is registered but disabled by default."""
    from homeassistant.helpers import entity_registry as er

    entry = _make_entry(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    entity_id = ent_reg.async_get_entity_id("binary_sensor", DOMAIN, f"{MOCK_DOMAIN}_whois_privacy")
    assert entity_id is not None
    entity_entry = ent_reg.async_get(entity_id)
    assert entity_entry is not None
    assert entity_entry.disabled_by is not None


async def test_whois_privacy_sensor_value(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test WHOIS privacy sensor shows correct value when domain info is available."""
    from homeassistant.helpers import entity_registry as er

    from custom_components.porkbun_ddns.api import DomainInfo

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

    # Enable the disabled-by-default sensor
    ent_reg = er.async_get(hass)
    entity_id = ent_reg.async_get_entity_id("binary_sensor", DOMAIN, f"{MOCK_DOMAIN}_whois_privacy")
    assert entity_id is not None
    ent_reg.async_update_entity(entity_id, disabled_by=None)

    # Reload to pick up the enabled sensor
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "on"  # WHOIS privacy is enabled


async def test_health_sensor_extra_attributes_with_failures(
    hass: HomeAssistant, mock_porkbun_client: AsyncMock
) -> None:
    """Test health sensor extra_state_attributes includes failed_records."""
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

    state = hass.states.get(_get_entity_id(hass, "binary_sensor", f"{MOCK_DOMAIN}_health"))
    assert state is not None
    assert "failed_records" in state.attributes


async def test_health_sensor_attributes_include_managed_subdomains(
    hass: HomeAssistant, mock_porkbun_client: AsyncMock
) -> None:
    """Test health sensor exposes managed subdomains and per-record status details."""
    entry = _make_entry(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(_get_entity_id(hass, "binary_sensor", f"{MOCK_DOMAIN}_health"))
    assert state is not None
    assert state.attributes["managed_subdomains"] == ["@", "www"]
    assert len(state.attributes["record_status"]) == 2
