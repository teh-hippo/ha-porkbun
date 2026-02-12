"""Sensor entities for Porkbun DDNS."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
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
    """Set up Porkbun DDNS sensors from a config entry."""
    coordinator: PorkbunDdnsCoordinator = hass.data[DOMAIN][entry.entry_id]
    domain_name = entry.data[CONF_DOMAIN]

    entities: list[SensorEntity] = []

    # Device-level sensors (one per TLD)
    entities.append(DdnsLastUpdatedSensor(coordinator, domain_name))
    entities.append(DdnsNextUpdateSensor(coordinator, domain_name))

    # Per-subdomain IP sensors
    targets = [""] + coordinator.subdomains
    for subdomain in targets:
        if coordinator.ipv4_enabled:
            entities.append(DdnsIpSensor(coordinator, domain_name, subdomain, "A"))
        if coordinator.ipv6_enabled:
            entities.append(DdnsIpSensor(coordinator, domain_name, subdomain, "AAAA"))

    async_add_entities(entities)


def _device_info(domain_name: str) -> DeviceInfo:
    """Return shared device info for all sensors under a domain."""
    return DeviceInfo(
        identifiers={(DOMAIN, domain_name)},
        name=domain_name,
        manufacturer="Porkbun",
        model="DDNS",
        entry_type=DeviceEntryType.SERVICE,
        configuration_url=f"https://porkbun.com/account/domainsSpe498/{domain_name}",
    )


class DdnsIpSensor(CoordinatorEntity[PorkbunDdnsCoordinator], SensorEntity):
    """Sensor showing the current IP address for a DNS record."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PorkbunDdnsCoordinator,
        domain_name: str,
        subdomain: str,
        record_type: str,
    ) -> None:
        """Initialize the IP sensor."""
        super().__init__(coordinator)
        self._subdomain = subdomain
        self._record_type = record_type
        ip_version = "IPv4" if record_type == "A" else "IPv6"

        # Name: "IPv4" for root, "ha.totesnotexternal IPv4" for subdomain
        if subdomain:
            self._attr_name = f"{subdomain} {ip_version}"
        else:
            self._attr_name = ip_version

        self._attr_unique_id = f"{domain_name}_{subdomain or '@'}_{record_type}_ip"
        self._attr_icon = "mdi:ip-network"
        self._attr_device_info = _device_info(domain_name)

    @property
    def native_value(self) -> str | None:
        """Return the current IP address."""
        if not self.coordinator.data:
            return None
        key = self.coordinator.data.record_key(self._subdomain, self._record_type)
        state = self.coordinator.data.records.get(key)
        return state.current_ip if state else None


class DdnsLastUpdatedSensor(CoordinatorEntity[PorkbunDdnsCoordinator], SensorEntity):
    """Device-level sensor showing when records were last checked."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-check-outline"

    def __init__(
        self,
        coordinator: PorkbunDdnsCoordinator,
        domain_name: str,
    ) -> None:
        """Initialize the last updated sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{domain_name}_last_updated"
        self._attr_name = "Last Updated"
        self._attr_device_info = _device_info(domain_name)

    @property
    def native_value(self) -> datetime | None:
        """Return the last updated timestamp."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.last_updated


class DdnsNextUpdateSensor(CoordinatorEntity[PorkbunDdnsCoordinator], SensorEntity):
    """Device-level sensor showing when the next update check is scheduled."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-fast"

    def __init__(
        self,
        coordinator: PorkbunDdnsCoordinator,
        domain_name: str,
    ) -> None:
        """Initialize the next update sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{domain_name}_next_update"
        self._attr_name = "Next Update"
        self._attr_device_info = _device_info(domain_name)

    @property
    def native_value(self) -> datetime | None:
        """Return the next scheduled update timestamp."""
        if not self.coordinator.data or not self.coordinator.data.last_updated:
            return None
        interval = self.coordinator.update_interval
        if interval is None:
            return None
        return self.coordinator.data.last_updated + interval
