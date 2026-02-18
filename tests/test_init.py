"""Tests for integration setup and unload."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.porkbun_ddns.api import PorkbunApiError, PorkbunAuthError
from custom_components.porkbun_ddns.const import DEFAULT_UPDATE_INTERVAL, DOMAIN
from custom_components.porkbun_ddns.coordinator import PorkbunDdnsCoordinator

from .conftest import MOCK_DOMAIN, MOCK_IPV4, make_entry


@pytest.fixture(autouse=True)
def _enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations."""


async def test_setup_entry(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test successful setup of a config entry."""
    entry = make_entry(hass)

    result = await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert result is True
    assert isinstance(entry.runtime_data, PorkbunDdnsCoordinator)


async def test_setup_entry_auth_failure_sets_setup_error(
    hass: HomeAssistant, mock_porkbun_client: AsyncMock
) -> None:
    """Test auth failures are surfaced as SETUP_ERROR."""
    mock_porkbun_client.ping.side_effect = PorkbunAuthError("Invalid key")
    entry = make_entry(hass)

    result = await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert result is False
    assert entry.state is ConfigEntryState.SETUP_ERROR


async def test_setup_entry_api_failure_sets_setup_retry(
    hass: HomeAssistant, mock_porkbun_client: AsyncMock
) -> None:
    """Test transient API failures are surfaced as SETUP_RETRY."""
    mock_porkbun_client.ping.side_effect = PorkbunApiError("Temporary outage")
    entry = make_entry(hass)

    result = await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert result is False
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_unload_entry(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test unloading a config entry."""
    entry = make_entry(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.async_unload(entry.entry_id)
    assert result is True


async def test_coordinator_polls_on_time_change(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test coordinator performs scheduled polling when time advances."""
    updated_ipv4 = "5.6.7.8"
    mock_porkbun_client.ping.side_effect = [MOCK_IPV4, updated_ipv4]
    entry = make_entry(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    first_call_count = mock_porkbun_client.ping.call_count
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=DEFAULT_UPDATE_INTERVAL + 1))
    await hass.async_block_till_done()

    assert mock_porkbun_client.ping.call_count > first_call_count
    assert entry.runtime_data.data.public_ipv4 == updated_ipv4


async def test_remove_stale_device(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test that a stale (non-matching) device can be removed."""
    entry = make_entry(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    dev_reg = dr.async_get(hass)
    # Create a stale device with a different identifier
    stale_device = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "old-domain.com")},
        name="old-domain.com",
    )

    from custom_components.porkbun_ddns import async_remove_config_entry_device

    assert await async_remove_config_entry_device(hass, entry, stale_device) is True


async def test_cannot_remove_active_device(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test that an active device cannot be removed."""
    entry = make_entry(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    dev_reg = dr.async_get(hass)
    active_device = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, MOCK_DOMAIN)},
        name=MOCK_DOMAIN,
    )

    from custom_components.porkbun_ddns import async_remove_config_entry_device

    assert await async_remove_config_entry_device(hass, entry, active_device) is False
