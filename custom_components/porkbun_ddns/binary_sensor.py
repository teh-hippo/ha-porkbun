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

from . import PorkbunDdnsConfigEntry
from .coordinator import PorkbunDdnsCoordinator

PARALLEL_UPDATES = 0


class _DdnsBinarySensorBase(CoordinatorEntity[PorkbunDdnsCoordinator], BinarySensorEntity):
    _attr_has_entity_name = True
    _unique_id_suffix: str

    def __init__(self, coordinator: PorkbunDdnsCoordinator, domain_name: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{domain_name}_{self._unique_id_suffix}"
        self._attr_device_info = coordinator.device_info


class DdnsHealthSensor(_DdnsBinarySensorBase):
    """Binary sensor showing DDNS health status (problem class: off = healthy ✅)."""

    _unique_id_suffix = "health"
    _attr_translation_key = "dns_status"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

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
        attrs: dict[str, str | list[str]] = {
            "summary": f"{ok}/{total} OK",
            "managed_subdomains": ["@"] + coord.subdomains,
        }

        if coord.data.records:
            attrs["record_status"] = [
                f"{record_key}: {'OK' if state.ok else f'ERROR ({state.error})'}"
                for record_key, state in sorted(coord.data.records.items())
            ]

            failed = [k for k, v in coord.data.records.items() if not v.ok]
            if failed:
                attrs["failed_records"] = failed

        return attrs


class DdnsWhoisPrivacySensor(_DdnsBinarySensorBase):
    """Binary sensor showing WHOIS privacy status."""

    _unique_id_suffix = "whois_privacy"
    _attr_translation_key = "whois_privacy"
    _attr_entity_registry_enabled_default = False
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_on(self) -> bool | None:
        """Return True if WHOIS privacy is enabled."""
        if (info := self.coordinator.data.domain_info) is None:
            return None
        return info.whois_privacy


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PorkbunDdnsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Porkbun DDNS binary sensors from a config entry."""
    coordinator = entry.runtime_data
    domain_name = coordinator.domain

    async_add_entities(
        [
            DdnsHealthSensor(coordinator, domain_name),
            DdnsWhoisPrivacySensor(coordinator, domain_name),
        ]
    )
