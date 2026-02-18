"""Tests for the button entity."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.porkbun_ddns.const import DOMAIN

from .conftest import MOCK_DOMAIN, make_entry


@pytest.fixture(autouse=True)
def _enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations."""


async def test_button_created(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test that the force update button is created."""
    entry = make_entry(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    states = {s.entity_id: s for s in hass.states.async_all()}
    button_ids = [eid for eid in states if eid.startswith("button.")]
    assert len(button_ids) == 1


async def test_button_press_triggers_refresh(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test that pressing the button triggers a coordinator refresh."""
    entry = make_entry(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Press the button
    ent_reg = er.async_get(hass)
    button_id = ent_reg.async_get_entity_id("button", DOMAIN, f"{MOCK_DOMAIN}_force_update")
    assert button_id is not None
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": button_id},
        blocking=True,
    )

    # Ping is called on setup + once on button press
    assert mock_porkbun_client.ping.call_count >= 2


async def test_button_has_clear_name(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test force update button has a descriptive user-facing name."""
    entry = make_entry(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    button_id = ent_reg.async_get_entity_id("button", DOMAIN, f"{MOCK_DOMAIN}_force_update")
    assert button_id is not None

    state = hass.states.get(button_id)
    assert state is not None
    assert state.name is not None
    assert "Refresh DDNS Records" in state.name
