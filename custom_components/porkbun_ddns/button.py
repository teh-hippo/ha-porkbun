"""Button entities for Porkbun DDNS."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DOMAIN, DOMAIN
from .coordinator import PorkbunDdnsCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Porkbun DDNS buttons from a config entry."""
    coordinator: PorkbunDdnsCoordinator = hass.data[DOMAIN][entry.entry_id]
    domain_name = entry.data[CONF_DOMAIN]
    async_add_entities([DdnsForceUpdateButton(coordinator, domain_name)])


class DdnsForceUpdateButton(CoordinatorEntity[PorkbunDdnsCoordinator], ButtonEntity):
    """Button to trigger an immediate DDNS update."""

    _attr_has_entity_name = True
    _attr_name = "Update DNS"
    _attr_icon = "mdi:refresh"

    def __init__(
        self,
        coordinator: PorkbunDdnsCoordinator,
        domain_name: str,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{domain_name}_force_update"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, domain_name)},
            name=domain_name,
            manufacturer="Porkbun",
            model="DDNS",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=f"https://porkbun.com/account/domainsSpe498/{domain_name}",
        )

    async def async_press(self) -> None:
        """Trigger an immediate coordinator refresh."""
        await self.coordinator.async_request_refresh()
