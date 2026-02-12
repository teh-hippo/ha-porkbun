"""Porkbun DDNS integration for Home Assistant."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import CONF_DOMAIN, DOMAIN, LOGGER
from .coordinator import PorkbunDdnsCoordinator

PLATFORMS = ["binary_sensor", "button", "sensor"]

type PorkbunDdnsConfigEntry = ConfigEntry


async def async_setup_entry(hass: HomeAssistant, entry: PorkbunDdnsConfigEntry) -> bool:
    """Set up Porkbun DDNS from a config entry."""
    coordinator = PorkbunDdnsCoordinator(hass, entry)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    # Clear any previous repair issues for this domain
    ir.async_delete_issue(hass, DOMAIN, f"api_access_{entry.data[CONF_DOMAIN]}")

    LOGGER.debug("Porkbun DDNS set up for %s", entry.data[CONF_DOMAIN])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: PorkbunDdnsConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: PorkbunDdnsConfigEntry) -> None:
    """Handle options update — reload the entry to pick up new settings."""
    await hass.config_entries.async_reload(entry.entry_id)
