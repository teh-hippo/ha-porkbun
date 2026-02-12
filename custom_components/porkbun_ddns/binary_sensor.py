"""Binary sensor entities for Porkbun DDNS."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import PorkbunDdnsConfigEntry
from .const import CONF_DOMAIN, DOMAIN
from .coordinator import PorkbunDdnsCoordinator

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PorkbunDdnsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Porkbun DDNS binary sensors from a config entry."""
    coordinator = entry.runtime_data
    domain_name = entry.data[CONF_DOMAIN]
    async_add_entities([DdnsHealthSensor(coordinator, domain_name)])


class DdnsHealthSensor(CoordinatorEntity[PorkbunDdnsCoordinator], BinarySensorEntity):
    """Binary sensor showing DDNS health status (problem class: off = healthy ✅)."""

    _attr_has_entity_name = True
    _attr_name = "DNS Status"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(
        self,
        coordinator: PorkbunDdnsCoordinator,
        domain_name: str,
    ) -> None:
        """Initialize the health sensor."""
        super().__init__(coordinator)
        self._domain_name = domain_name
        self._attr_unique_id = f"{domain_name}_health"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, domain_name)},
            name=domain_name,
            manufacturer="Porkbun",
            model="DDNS",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=f"https://porkbun.com/account/domainsSpe498/{domain_name}",
        )

    @property
    def is_on(self) -> bool | None:
        """Return True if there IS a problem (problem class is inverted)."""
        if not self.coordinator.data or not self.coordinator.data.records:
            return None
        return not self.coordinator.all_ok

    @property
    def extra_state_attributes(self) -> dict:
        """Return detailed record status."""
        coord = self.coordinator
        total = coord.record_count
        ok = coord.ok_count
        attrs: dict = {"summary": f"{ok}/{total} OK"}

        # List any failed records
        if coord.data and coord.data.records:
            failed = [k for k, v in coord.data.records.items() if not v.ok]
            if failed:
                attrs["failed_records"] = failed

        return attrs
