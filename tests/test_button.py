"""Tests for the button entity."""

from __future__ import annotations

from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant

from .conftest import MOCK_DOMAIN, get_entity_id, make_entry, setup_entry


async def test_button_present_and_named(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    entry = make_entry(hass)
    await setup_entry(hass, entry)

    button_id = get_entity_id(hass, "button", f"{MOCK_DOMAIN}_force_update")
    state = hass.states.get(button_id)
    assert state is not None
    assert "Refresh DDNS Records" in (state.name or "")


async def test_button_press_triggers_refresh(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    entry = make_entry(hass)
    await setup_entry(hass, entry)

    button_id = get_entity_id(hass, "button", f"{MOCK_DOMAIN}_force_update")
    await hass.services.async_call("button", "press", {"entity_id": button_id}, blocking=True)

    assert mock_porkbun_client.ping.call_count >= 2
