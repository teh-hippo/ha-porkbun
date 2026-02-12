"""Tests for the DDNS coordinator."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.porkbun_ddns.api import DnsRecord, PorkbunApiError, PorkbunAuthError
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
from custom_components.porkbun_ddns.coordinator import PorkbunDdnsCoordinator

from .conftest import MOCK_API_KEY, MOCK_DOMAIN, MOCK_IPV4, MOCK_SECRET_KEY


@pytest.fixture(autouse=True)
def _enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations."""


def _make_entry(hass: HomeAssistant, **options) -> MockConfigEntry:
    """Create a mock config entry."""
    defaults = {
        CONF_SUBDOMAINS: [],
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


async def test_coordinator_creates_record_if_missing(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test coordinator creates a DNS record when none exists."""
    entry = _make_entry(hass)
    coordinator = PorkbunDdnsCoordinator(hass, entry)

    data = await coordinator._async_update_data()

    assert data.public_ipv4 == MOCK_IPV4
    mock_porkbun_client.create_record.assert_called_once()
    record_state = data.records.get("@_A")
    assert record_state is not None
    assert record_state.current_ip == MOCK_IPV4


async def test_coordinator_skips_when_ip_matches(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test coordinator skips update when IP already matches."""
    mock_porkbun_client.get_records.return_value = [
        DnsRecord(id="123", name="example.com", record_type="A", content=MOCK_IPV4, ttl="600", prio="0", notes="")
    ]
    entry = _make_entry(hass)
    coordinator = PorkbunDdnsCoordinator(hass, entry)

    data = await coordinator._async_update_data()

    mock_porkbun_client.create_record.assert_not_called()
    mock_porkbun_client.edit_record_by_name_type.assert_not_called()
    assert data.records["@_A"].current_ip == MOCK_IPV4


async def test_coordinator_updates_when_ip_differs(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test coordinator updates record when IP has changed."""
    mock_porkbun_client.get_records.return_value = [
        DnsRecord(id="123", name="example.com", record_type="A", content="9.9.9.9", ttl="600", prio="0", notes="")
    ]
    entry = _make_entry(hass)
    coordinator = PorkbunDdnsCoordinator(hass, entry)

    data = await coordinator._async_update_data()

    mock_porkbun_client.edit_record_by_name_type.assert_called_once()
    assert data.records["@_A"].current_ip == MOCK_IPV4


async def test_coordinator_auth_error(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test coordinator raises ConfigEntryAuthFailed on auth error."""
    mock_porkbun_client.ping.side_effect = PorkbunAuthError("Invalid key")
    entry = _make_entry(hass)
    coordinator = PorkbunDdnsCoordinator(hass, entry)

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


async def test_coordinator_api_error(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test coordinator raises UpdateFailed on API error."""
    mock_porkbun_client.ping.side_effect = PorkbunApiError("Server error")
    entry = _make_entry(hass)
    coordinator = PorkbunDdnsCoordinator(hass, entry)

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_coordinator_with_subdomains(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test coordinator processes both root and subdomains."""
    entry = _make_entry(hass, **{CONF_SUBDOMAINS: ["www", "vpn"]})
    coordinator = PorkbunDdnsCoordinator(hass, entry)

    data = await coordinator._async_update_data()

    # Should create records for root + www + vpn
    assert mock_porkbun_client.create_record.call_count == 3
    assert "@_A" in data.records
    assert "www_A" in data.records
    assert "vpn_A" in data.records
