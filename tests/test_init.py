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

from custom_components.porkbun_ddns import async_remove_config_entry_device
from custom_components.porkbun_ddns.api import PorkbunApiError, PorkbunAuthError
from custom_components.porkbun_ddns.const import DEFAULT_UPDATE_INTERVAL, DOMAIN
from custom_components.porkbun_ddns.coordinator import PorkbunDdnsCoordinator

from .conftest import MOCK_DOMAIN, MOCK_IPV4, make_entry, setup_entry


async def test_setup_and_unload_entry(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    entry = make_entry(hass)
    assert await setup_entry(hass, entry) is True
    assert isinstance(entry.runtime_data, PorkbunDdnsCoordinator)

    assert await hass.config_entries.async_unload(entry.entry_id) is True


@pytest.mark.parametrize(
    ("side_effect", "expected_state"),
    [
        (PorkbunAuthError("Invalid key"), ConfigEntryState.SETUP_ERROR),
        (PorkbunApiError("Temporary outage"), ConfigEntryState.SETUP_RETRY),
    ],
)
async def test_setup_failure_states(
    hass: HomeAssistant,
    mock_porkbun_client: AsyncMock,
    side_effect: Exception,
    expected_state: ConfigEntryState,
) -> None:
    mock_porkbun_client.ping.side_effect = side_effect
    entry = make_entry(hass)

    assert await setup_entry(hass, entry) is False
    assert entry.state is expected_state


async def test_coordinator_polls_on_time_change(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    mock_porkbun_client.ping.side_effect = [MOCK_IPV4, "5.6.7.8"]
    entry = make_entry(hass)
    await setup_entry(hass, entry)

    first_call_count = mock_porkbun_client.ping.call_count
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=DEFAULT_UPDATE_INTERVAL + 1))
    await hass.async_block_till_done()

    assert mock_porkbun_client.ping.call_count > first_call_count
    assert entry.runtime_data.data.public_ipv4 == "5.6.7.8"


@pytest.mark.parametrize(
    ("identifiers", "can_remove"),
    [
        ({(DOMAIN, "old-domain.com")}, True),
        ({(DOMAIN, MOCK_DOMAIN)}, False),
    ],
)
async def test_remove_config_entry_device_rules(
    hass: HomeAssistant,
    mock_porkbun_client: AsyncMock,
    identifiers: set[tuple[str, str]],
    can_remove: bool,
) -> None:
    entry = make_entry(hass)
    await setup_entry(hass, entry)

    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers=identifiers,
        name=next(iter(identifiers))[1],
    )

    assert await async_remove_config_entry_device(hass, entry, device) is can_remove
