"""Snapshot tests for entity platform metadata/states."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import snapshot_platform
from syrupy.assertion import SnapshotAssertion

from .conftest import make_entry


@pytest.fixture(autouse=True)
def _enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations."""


async def _snapshot_single_platform(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
    freezer,
    platform: Platform,
) -> None:
    """Set up and snapshot a single platform for one config entry."""
    freezer.move_to("2026-02-18 12:00:00+00:00")
    entry = make_entry(hass, subdomains=["www"])

    with patch("custom_components.porkbun_ddns.PLATFORMS", [platform]):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        entity_registry = er.async_get(hass)
        for entity_entry in er.async_entries_for_config_entry(entity_registry, entry.entry_id):
            if entity_entry.disabled_by is not None:
                entity_registry.async_update_entity(entity_entry.entity_id, disabled_by=None)

        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()

        await snapshot_platform(hass, entity_registry, snapshot, entry.entry_id)


async def test_snapshot_sensor_platform(
    hass: HomeAssistant,
    mock_porkbun_client: AsyncMock,
    snapshot: SnapshotAssertion,
    freezer,
) -> None:
    """Snapshot the sensor platform."""
    await _snapshot_single_platform(hass, snapshot, freezer, Platform.SENSOR)


async def test_snapshot_binary_sensor_platform(
    hass: HomeAssistant,
    mock_porkbun_client: AsyncMock,
    snapshot: SnapshotAssertion,
    freezer,
) -> None:
    """Snapshot the binary_sensor platform."""
    await _snapshot_single_platform(hass, snapshot, freezer, Platform.BINARY_SENSOR)


async def test_snapshot_button_platform(
    hass: HomeAssistant,
    mock_porkbun_client: AsyncMock,
    snapshot: SnapshotAssertion,
    freezer,
) -> None:
    """Snapshot the button platform."""
    await _snapshot_single_platform(hass, snapshot, freezer, Platform.BUTTON)
