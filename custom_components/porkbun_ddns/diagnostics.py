"""Diagnostics for Porkbun DDNS."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import PorkbunDdnsConfigEntry

REDACT_KEYS = {"api_key", "secret_key"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: PorkbunDdnsConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    data = coordinator.data

    records = {key: asdict(state) for key, state in data.records.items()}

    domain_info: dict[str, Any] | None = None
    if data.domain_info:
        domain_info = asdict(data.domain_info)

    return {
        "config": async_redact_data(dict(entry.data), REDACT_KEYS),
        "options": dict(entry.options),
        "coordinator": {
            "domain": coordinator.domain,
            "ipv4_enabled": coordinator.ipv4_enabled,
            "ipv6_enabled": coordinator.ipv6_enabled,
            "record_count": coordinator.record_count,
            "ok_count": coordinator.ok_count,
            "all_ok": coordinator.all_ok,
            "public_ipv4": data.public_ipv4,
            "public_ipv6": data.public_ipv6,
            "last_updated": str(data.last_updated) if data.last_updated else None,
            "records": records,
            "domain_info": domain_info,
        },
    }
