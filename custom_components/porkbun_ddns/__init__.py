"""Porkbun DDNS integration for Home Assistant."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.event import async_track_point_in_utc_time

from .const import CONF_DOMAIN, DOMAIN
from .coordinator import PorkbunDdnsCoordinator

PLATFORMS = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.SENSOR]

type PorkbunDdnsConfigEntry = ConfigEntry[PorkbunDdnsCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: PorkbunDdnsConfigEntry) -> bool:
    """Set up Porkbun DDNS from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    coordinator = PorkbunDdnsCoordinator(hass, entry)

    await coordinator.async_config_entry_first_refresh()

    if coordinator.data.last_updated is None and coordinator.startup_delay_remaining > 0:

        def _schedule_startup_refresh(_: object) -> None:
            hass.add_job(coordinator.async_request_refresh())

        entry.async_on_unload(
            async_track_point_in_utc_time(
                hass,
                _schedule_startup_refresh,
                coordinator.startup_delay_until,
            )
        )

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: PorkbunDdnsConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_config_entry_device(
    hass: HomeAssistant,
    config_entry: PorkbunDdnsConfigEntry,
    device_entry: dr.DeviceEntry,
) -> bool:
    """Allow removal of a device if it is no longer active."""
    domain_name: str = config_entry.data[CONF_DOMAIN]
    return (DOMAIN, domain_name) not in device_entry.identifiers
