"""Porkbun DDNS integration for Home Assistant."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

from .const import CONF_DOMAIN, DOMAIN
from .coordinator import PorkbunDdnsCoordinator

PLATFORMS = ["binary_sensor", "button", "sensor"]

type PorkbunDdnsConfigEntry = ConfigEntry[PorkbunDdnsCoordinator]


def device_info(domain_name: str) -> DeviceInfo:
    """Return shared device info for all entities under a domain."""
    return DeviceInfo(
        identifiers={(DOMAIN, domain_name)},
        name=domain_name,
        manufacturer="Porkbun",
        model="DDNS",
        entry_type=DeviceEntryType.SERVICE,
        configuration_url="https://porkbun.com/account/domains",
    )


async def async_setup_entry(hass: HomeAssistant, entry: PorkbunDdnsConfigEntry) -> bool:
    """Set up Porkbun DDNS from a config entry."""
    coordinator = PorkbunDdnsCoordinator(hass, entry)

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: PorkbunDdnsConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(hass: HomeAssistant, entry: PorkbunDdnsConfigEntry) -> None:
    """Handle options update — reload the entry to pick up new settings."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_config_entry_device(
    hass: HomeAssistant,
    config_entry: PorkbunDdnsConfigEntry,
    device_entry: dr.DeviceEntry,
) -> bool:
    """Allow removal of a device if it is no longer active."""
    domain_name: str = config_entry.data[CONF_DOMAIN]
    return not any(identifier for identifier in device_entry.identifiers if identifier == (DOMAIN, domain_name))
