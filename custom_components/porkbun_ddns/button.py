"""Button entities for Porkbun DDNS."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import PorkbunDdnsConfigEntry, device_info
from .const import CONF_DOMAIN
from .coordinator import PorkbunDdnsCoordinator

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PorkbunDdnsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Porkbun DDNS buttons from a config entry."""
    coordinator = entry.runtime_data
    domain_name = entry.data[CONF_DOMAIN]
    async_add_entities([DdnsForceUpdateButton(coordinator, domain_name)])


class DdnsForceUpdateButton(CoordinatorEntity[PorkbunDdnsCoordinator], ButtonEntity):
    """Button to trigger an immediate DDNS update."""

    _attr_has_entity_name = True
    _attr_translation_key = "update_dns"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: PorkbunDdnsCoordinator,
        domain_name: str,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{domain_name}_force_update"
        self._attr_device_info = device_info(domain_name)

    async def async_press(self) -> None:
        """Trigger an immediate coordinator refresh."""
        await self.coordinator.async_request_refresh()
