"""Sensor entities for Porkbun DDNS."""

from __future__ import annotations

from datetime import UTC, datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
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
    """Set up Porkbun DDNS sensors from a config entry."""
    coordinator = entry.runtime_data
    domain_name = entry.data[CONF_DOMAIN]

    entities: list[SensorEntity] = []

    # All sensors are device-level (one per TLD)
    if coordinator.ipv4_enabled:
        entities.append(DdnsIpSensor(coordinator, domain_name, "A"))
    if coordinator.ipv6_enabled:
        entities.append(DdnsIpSensor(coordinator, domain_name, "AAAA"))
    entities.append(DdnsLastUpdatedSensor(coordinator, domain_name))
    entities.append(DdnsNextUpdateSensor(coordinator, domain_name))
    entities.append(DdnsDomainExpirySensor(coordinator, domain_name))

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
    """Device-level sensor showing the current public IP address."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:ip-network"
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: PorkbunDdnsCoordinator,
        domain_name: str,
        record_type: str,
    ) -> None:
        """Initialize the IP sensor."""
        super().__init__(coordinator)
        self._record_type = record_type
        self._domain_name = domain_name
        ip_version = "IPv4" if record_type == "A" else "IPv6"
        self._attr_name = f"Public {ip_version}"
        self._attr_unique_id = f"{domain_name}_{record_type}_ip"
        self._attr_device_info = _device_info(domain_name)

    @property
    def native_value(self) -> str | None:
        """Return the current public IP address."""
        if not self.coordinator.data:
            return None
        if self._record_type == "A":
            return self.coordinator.data.public_ipv4
        return self.coordinator.data.public_ipv6

    @property
    def extra_state_attributes(self) -> dict[str, str | list[str]]:
        """Return managed DNS records as attributes."""
        targets = [""] + self.coordinator.subdomains
        records = []
        for sub in targets:
            fqdn = f"{sub}.{self._domain_name}" if sub else self._domain_name
            records.append(fqdn)
        return {"managed_records": records}


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


class DdnsDomainExpirySensor(CoordinatorEntity[PorkbunDdnsCoordinator], SensorEntity):
    """Sensor showing when the domain registration expires."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:calendar-clock"
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: PorkbunDdnsCoordinator,
        domain_name: str,
    ) -> None:
        """Initialize the domain expiry sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{domain_name}_domain_expiry"
        self._attr_name = "Domain Expiry"
        self._attr_device_info = _device_info(domain_name)

    @property
    def native_value(self) -> datetime | None:
        """Return the domain expiry date as a UTC timestamp."""
        if not self.coordinator.data or not self.coordinator.data.domain_info:
            return None
        raw = self.coordinator.data.domain_info.expire_date
        if not raw:
            return None
        try:
            return datetime.strptime(raw, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
        except ValueError:
            return None
