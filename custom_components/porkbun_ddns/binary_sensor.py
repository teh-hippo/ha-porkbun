"""Binary sensor entities for Porkbun DDNS."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
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
    """Set up Porkbun DDNS binary sensors from a config entry."""
    coordinator = entry.runtime_data
    domain_name = entry.data[CONF_DOMAIN]
    async_add_entities(
        [
            DdnsHealthSensor(coordinator, domain_name),
            DdnsWhoisPrivacySensor(coordinator, domain_name),
        ]
    )


class DdnsHealthSensor(CoordinatorEntity[PorkbunDdnsCoordinator], BinarySensorEntity):
    """Binary sensor showing DDNS health status (problem class: off = healthy ✅)."""

    _attr_has_entity_name = True
    _attr_translation_key = "dns_status"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(
        self,
        coordinator: PorkbunDdnsCoordinator,
        domain_name: str,
    ) -> None:
        """Initialize the health sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{domain_name}_health"
        self._attr_device_info = device_info(domain_name)

    @property
    def is_on(self) -> bool | None:
        """Return True if there IS a problem (problem class is inverted)."""
        if not self.coordinator.data.records:
            return None
        return not self.coordinator.all_ok

    @property
    def extra_state_attributes(self) -> dict[str, str | list[str]]:
        """Return detailed record status."""
        coord = self.coordinator
        total = coord.record_count
        ok = coord.ok_count
        attrs: dict[str, str | list[str]] = {"summary": f"{ok}/{total} OK"}

        if coord.data.records:
            failed = [k for k, v in coord.data.records.items() if not v.ok]
            if failed:
                attrs["failed_records"] = failed

        return attrs


class DdnsWhoisPrivacySensor(CoordinatorEntity[PorkbunDdnsCoordinator], BinarySensorEntity):
    """Binary sensor showing WHOIS privacy status."""

    _attr_has_entity_name = True
    _attr_translation_key = "whois_privacy"
    _attr_entity_registry_enabled_default = False
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: PorkbunDdnsCoordinator,
        domain_name: str,
    ) -> None:
        """Initialize the WHOIS privacy sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{domain_name}_whois_privacy"
        self._attr_device_info = device_info(domain_name)

    @property
    def is_on(self) -> bool | None:
        """Return True if WHOIS privacy is enabled."""
        if not self.coordinator.data.domain_info:
            return None
        return self.coordinator.data.domain_info.whois_privacy
