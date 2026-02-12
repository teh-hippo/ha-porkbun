"""Tests for the button entity."""

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
            CONF_SUBDOMAINS: [],
            CONF_IPV4: True,
            CONF_IPV6: False,
            CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
        },
    )
    entry.add_to_hass(hass)
    return entry


async def test_button_created(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test that the force update button is created."""
    entry = _make_entry(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    states = {s.entity_id: s for s in hass.states.async_all()}
    button_ids = [eid for eid in states if eid.startswith("button.")]
    assert len(button_ids) == 1


async def test_button_press_triggers_refresh(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test that pressing the button triggers a coordinator refresh."""
    entry = _make_entry(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Press the button
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": f"button.{MOCK_DOMAIN.replace('.', '_')}_update_dns"},
        blocking=True,
    )

    # Ping is called on setup + once on button press
    assert mock_porkbun_client.ping.call_count >= 2
