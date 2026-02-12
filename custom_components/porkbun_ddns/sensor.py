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
from .coordinator import PorkbunDdnsCoordinator, RecordState


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Porkbun DDNS sensors from a config entry."""
    coordinator: PorkbunDdnsCoordinator = hass.data[DOMAIN][entry.entry_id]
    domain_name = entry.data[CONF_DOMAIN]

    entities: list[SensorEntity] = []

    # Root domain + subdomains
    targets = [""] + coordinator.subdomains
    for subdomain in targets:
        label = f"{subdomain}.{domain_name}" if subdomain else domain_name

        if coordinator.ipv4_enabled:
            entities.append(DdnsIpSensor(coordinator, domain_name, subdomain, "A", label))
        if coordinator.ipv6_enabled:
            entities.append(DdnsIpSensor(coordinator, domain_name, subdomain, "AAAA", label))
        entities.append(DdnsLastUpdatedSensor(coordinator, domain_name, subdomain, label))
        entities.append(DdnsLastChangedSensor(coordinator, domain_name, subdomain, label))
        entities.append(DdnsNextUpdateSensor(coordinator, domain_name, subdomain, label))

    async_add_entities(entities)


class DdnsBaseSensor(CoordinatorEntity[PorkbunDdnsCoordinator], SensorEntity):
    """Base class for DDNS sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PorkbunDdnsCoordinator,
        domain_name: str,
        subdomain: str,
        label: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._domain_name = domain_name
        self._subdomain = subdomain
        self._label = label
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, domain_name)},
            name=f"Porkbun DDNS: {domain_name}",
            manufacturer="Porkbun",
            entry_type=DeviceEntryType.SERVICE,
        )

    def _record_state(self, record_type: str) -> RecordState | None:
        """Get record state for this subdomain and type."""
        if not self.coordinator.data:
            return None
        key = self.coordinator.data.record_key(self._subdomain, record_type)
        return self.coordinator.data.records.get(key)


class DdnsIpSensor(DdnsBaseSensor):
    """Sensor showing the current IP address for a DNS record."""

    def __init__(
        self,
        coordinator: PorkbunDdnsCoordinator,
        domain_name: str,
        subdomain: str,
        record_type: str,
        label: str,
    ) -> None:
        """Initialize the IP sensor."""
        super().__init__(coordinator, domain_name, subdomain, label)
        self._record_type = record_type
        ip_version = "IPv4" if record_type == "A" else "IPv6"
        self._attr_unique_id = f"{domain_name}_{subdomain or '@'}_{record_type}_ip"
        self._attr_name = f"{label} {ip_version} Address"
        self._attr_icon = "mdi:ip-network"

    @property
    def native_value(self) -> str | None:
        """Return the current IP address."""
        state = self._record_state(self._record_type)
        return state.current_ip if state else None


class DdnsLastUpdatedSensor(DdnsBaseSensor):
    """Sensor showing when the record was last checked."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self,
        coordinator: PorkbunDdnsCoordinator,
        domain_name: str,
        subdomain: str,
        label: str,
    ) -> None:
        """Initialize the last updated sensor."""
        super().__init__(coordinator, domain_name, subdomain, label)
        self._attr_unique_id = f"{domain_name}_{subdomain or '@'}_last_updated"
        self._attr_name = f"{label} Last Updated"
        self._attr_icon = "mdi:clock-check-outline"

    @property
    def native_value(self) -> datetime | None:
        """Return the last updated timestamp."""
        # Use the first available record state for this subdomain
        if not self.coordinator.data:
            return None
        for rt in ("A", "AAAA"):
            state = self._record_state(rt)
            if state and state.last_updated:
                return state.last_updated
        return self.coordinator.data.last_updated


class DdnsLastChangedSensor(DdnsBaseSensor):
    """Sensor showing when the IP address last changed."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self,
        coordinator: PorkbunDdnsCoordinator,
        domain_name: str,
        subdomain: str,
        label: str,
    ) -> None:
        """Initialize the last changed sensor."""
        super().__init__(coordinator, domain_name, subdomain, label)
        self._attr_unique_id = f"{domain_name}_{subdomain or '@'}_last_changed"
        self._attr_name = f"{label} Last IP Change"
        self._attr_icon = "mdi:swap-horizontal"

    @property
    def native_value(self) -> datetime | None:
        """Return the last changed timestamp."""
        if not self.coordinator.data:
            return None
        latest: datetime | None = None
        for rt in ("A", "AAAA"):
            state = self._record_state(rt)
            if state and state.last_changed:
                if latest is None or state.last_changed > latest:
                    latest = state.last_changed
        return latest


class DdnsNextUpdateSensor(DdnsBaseSensor):
    """Sensor showing when the next update check is scheduled."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self,
        coordinator: PorkbunDdnsCoordinator,
        domain_name: str,
        subdomain: str,
        label: str,
    ) -> None:
        """Initialize the next update sensor."""
        super().__init__(coordinator, domain_name, subdomain, label)
        self._attr_unique_id = f"{domain_name}_{subdomain or '@'}_next_update"
        self._attr_name = f"{label} Next Update"
        self._attr_icon = "mdi:clock-fast"

    @property
    def native_value(self) -> datetime | None:
        """Return the next scheduled update timestamp."""
        if not self.coordinator.data or not self.coordinator.data.last_updated:
            return None
        return self.coordinator.data.last_updated + (
            self.coordinator.update_interval or __import__("datetime").timedelta(seconds=300)
        )
