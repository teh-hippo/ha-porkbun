"""Tests for diagnostics."""

from __future__ import annotations

from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant

from custom_components.porkbun_ddns.const import CONF_API_KEY, CONF_DOMAIN, CONF_SECRET_KEY, CONF_SUBDOMAINS
from custom_components.porkbun_ddns.diagnostics import async_get_config_entry_diagnostics

from .conftest import MOCK_DOMAIN, make_entry, setup_entry


async def test_diagnostics(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    entry = make_entry(hass, subdomains=["www"])
    await setup_entry(hass, entry)

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["config"][CONF_API_KEY] == "**REDACTED**"
    assert result["config"][CONF_SECRET_KEY] == "**REDACTED**"
    assert result["config"][CONF_DOMAIN] == MOCK_DOMAIN
    assert result["options"][CONF_SUBDOMAINS] == ["www"]
    assert result["coordinator"]["domain"] == MOCK_DOMAIN
    assert result["coordinator"]["record_count"] >= 1
