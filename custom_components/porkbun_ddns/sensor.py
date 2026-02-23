"""Sensor entities for Porkbun DDNS."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import PorkbunDdnsConfigEntry
from .coordinator import PorkbunDdnsCoordinator

PARALLEL_UPDATES = 0


_ValueFn = Callable[[PorkbunDdnsCoordinator], str | datetime | None]
_AttrsFn = Callable[[PorkbunDdnsCoordinator], dict[str, Any]]


@dataclass(frozen=True, kw_only=True)
class _SensorDef:
    unique_id: str
    translation_key: str
    value_fn: _ValueFn
    device_class: SensorDeviceClass | None = None
    entity_category: EntityCategory | None = None
    enabled_default: bool = True
    attrs_fn: _AttrsFn | None = None


class _DdnsSensor(CoordinatorEntity[PorkbunDdnsCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: PorkbunDdnsCoordinator, entity_def: _SensorDef) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = entity_def.unique_id
        self._attr_translation_key = entity_def.translation_key
        self._attr_device_info = coordinator.device_info
        self._attr_entity_registry_enabled_default = entity_def.enabled_default

        if entity_def.device_class is not None:
            self._attr_device_class = entity_def.device_class
        if entity_def.entity_category is not None:
            self._attr_entity_category = entity_def.entity_category

        self._value_fn = entity_def.value_fn
        self._attrs_fn = entity_def.attrs_fn

    @property
    def native_value(self) -> str | datetime | None:
        return self._value_fn(self.coordinator)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        return None if self._attrs_fn is None else self._attrs_fn(self.coordinator)


def _managed_records_attrs(coordinator: PorkbunDdnsCoordinator) -> dict[str, list[str]]:
    return {"managed_records": coordinator.managed_records}


def _next_update(coordinator: PorkbunDdnsCoordinator) -> datetime | None:
    last_updated = coordinator.data.last_updated
    interval = coordinator.update_interval
    if last_updated is None or interval is None:
        return None
    return last_updated + interval


def _domain_expiry(coordinator: PorkbunDdnsCoordinator) -> datetime | None:
    domain_info = coordinator.data.domain_info
    if domain_info is None or not domain_info.expire_date:
        return None
    try:
        return datetime.strptime(domain_info.expire_date, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    except ValueError:
        return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PorkbunDdnsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Porkbun DDNS sensors from a config entry."""
    coordinator = entry.runtime_data
    domain_name = coordinator.domain

    defs: list[_SensorDef] = [
        _SensorDef(
            unique_id=f"{domain_name}_managed_subdomains",
            translation_key="managed_subdomains",
            value_fn=lambda c: ", ".join(["@"] + c.subdomains),
            attrs_fn=_managed_records_attrs,
        ),
        _SensorDef(
            unique_id=f"{domain_name}_last_updated",
            translation_key="last_updated",
            value_fn=lambda c: c.data.last_updated,
            device_class=SensorDeviceClass.TIMESTAMP,
        ),
        _SensorDef(
            unique_id=f"{domain_name}_next_update",
            translation_key="next_update",
            value_fn=_next_update,
            device_class=SensorDeviceClass.TIMESTAMP,
        ),
        _SensorDef(
            unique_id=f"{domain_name}_domain_expiry",
            translation_key="domain_expiry",
            value_fn=_domain_expiry,
            device_class=SensorDeviceClass.TIMESTAMP,
            entity_category=EntityCategory.DIAGNOSTIC,
            enabled_default=False,
        ),
    ]

    if coordinator.ipv4_enabled:
        defs.append(
            _SensorDef(
                unique_id=f"{domain_name}_A_ip",
                translation_key="public_ipv4",
                value_fn=lambda c: c.data.public_ipv4,
                entity_category=EntityCategory.DIAGNOSTIC,
                enabled_default=False,
                attrs_fn=_managed_records_attrs,
            )
        )

    if coordinator.ipv6_enabled:
        defs.append(
            _SensorDef(
                unique_id=f"{domain_name}_AAAA_ip",
                translation_key="public_ipv6",
                value_fn=lambda c: c.data.public_ipv6,
                entity_category=EntityCategory.DIAGNOSTIC,
                enabled_default=False,
                attrs_fn=_managed_records_attrs,
            )
        )

    async_add_entities([_DdnsSensor(coordinator, entity_def) for entity_def in defs])
