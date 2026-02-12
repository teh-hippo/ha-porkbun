"""Tests for integration setup and unload."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
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
from custom_components.porkbun_ddns.coordinator import PorkbunDdnsCoordinator

from .conftest import MOCK_API_KEY, MOCK_DOMAIN, MOCK_SECRET_KEY


@pytest.fixture(autouse=True)
def _enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations."""


def _make_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create and add a mock config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCK_DOMAIN,
        data={
            CONF_API_KEY: MOCK_API_KEY,
            CONF_SECRET_KEY: MOCK_SECRET_KEY,
            CONF_DOMAIN: MOCK_DOMAIN,
        },
        options={
            CONF_SUBDOMAINS: [],
            CONF_IPV4: True,
            CONF_IPV6: False,
            CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
        },
    )
    entry.add_to_hass(hass)
    return entry


async def test_setup_entry(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test successful setup of a config entry."""
    entry = _make_entry(hass)

    result = await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert result is True
    assert isinstance(entry.runtime_data, PorkbunDdnsCoordinator)


async def test_unload_entry(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test unloading a config entry."""
    entry = _make_entry(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.async_unload(entry.entry_id)
    assert result is True


async def test_remove_stale_device(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test that a stale (non-matching) device can be removed."""
    entry = _make_entry(hass)
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
    entry = _make_entry(hass)
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
