"""Platform entity coverage tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .conftest import make_entry, setup_entry


async def _entity_ids_for_platform(
    hass: HomeAssistant,
    platform: Platform,
) -> set[str]:
    entry = make_entry(hass, subdomains=["www"])
    with patch("custom_components.porkbun_ddns.PLATFORMS", [platform]):
        await setup_entry(hass, entry)

    entity_registry = er.async_get(hass)
    for entity_entry in er.async_entries_for_config_entry(entity_registry, entry.entry_id):
        if entity_entry.disabled_by is not None:
            entity_registry.async_update_entity(entity_entry.entity_id, disabled_by=None)

    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    return {
        entity_state.entity_id
        for entity_state in hass.states.async_all()
        if entity_state.entity_id.startswith(f"{platform.value}.")
    }


@pytest.mark.parametrize(
    ("platform", "expected"),
    [
        (
            Platform.SENSOR,
            {
                "sensor.example_com_domain_expiry",
                "sensor.example_com_last_updated",
                "sensor.example_com_managed_subdomains",
                "sensor.example_com_next_update",
                "sensor.example_com_public_ipv4",
            },
        ),
        (Platform.BINARY_SENSOR, {"binary_sensor.example_com_dns_status", "binary_sensor.example_com_whois_privacy"}),
        (Platform.BUTTON, {"button.example_com_refresh_ddns_records"}),
    ],
)
async def test_platform_entities(
    hass: HomeAssistant,
    mock_porkbun_client: AsyncMock,
    platform: Platform,
    expected: set[str],
) -> None:
    assert await _entity_ids_for_platform(hass, platform) == expected
