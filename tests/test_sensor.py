"""Tests for sensor entities."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.porkbun_ddns.api import DomainInfo
from custom_components.porkbun_ddns.const import CONF_SUBDOMAINS

from .conftest import MOCK_DOMAIN, MOCK_IPV4, enable_entity, get_entity_id, make_entry, reload_entry, setup_entry


async def test_active_sensor_entities_created(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    entry = make_entry(hass)
    await setup_entry(hass, entry)

    sensor_ids = [state.entity_id for state in hass.states.async_all() if state.entity_id.startswith("sensor.")]
    assert sorted(sensor_ids) == [
        "sensor.example_com_last_updated",
        "sensor.example_com_managed_subdomains",
        "sensor.example_com_next_update",
    ]


async def test_managed_subdomains_sensor_updates_after_reload(
    hass: HomeAssistant,
    mock_porkbun_client: AsyncMock,
) -> None:
    entry = make_entry(hass, **{CONF_SUBDOMAINS: ["www"]})
    await setup_entry(hass, entry)

    entity_id = get_entity_id(hass, "sensor", f"{MOCK_DOMAIN}_managed_subdomains")
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "@, www"
    assert state.attributes["managed_records"] == [MOCK_DOMAIN, f"www.{MOCK_DOMAIN}"]

    hass.config_entries.async_update_entry(entry, options={**entry.options, CONF_SUBDOMAINS: ["www", "vpn"]})
    await reload_entry(hass, entry)

    updated_state = hass.states.get(entity_id)
    assert updated_state is not None
    assert updated_state.state == "@, www, vpn"
    assert updated_state.attributes["managed_records"] == [
        MOCK_DOMAIN,
        f"www.{MOCK_DOMAIN}",
        f"vpn.{MOCK_DOMAIN}",
    ]


@pytest.mark.parametrize("suffix", ["A_ip", "domain_expiry"])
async def test_disabled_by_default_sensors(
    hass: HomeAssistant,
    mock_porkbun_client: AsyncMock,
    suffix: str,
) -> None:
    entry = make_entry(hass)
    await setup_entry(hass, entry)

    entity_id = get_entity_id(hass, "sensor", f"{MOCK_DOMAIN}_{suffix}")
    entity_entry = er.async_get(hass).async_get(entity_id)
    assert entity_entry is not None
    assert entity_entry.disabled_by is not None


async def test_timestamp_sensor_values(
    hass: HomeAssistant,
    mock_porkbun_client: AsyncMock,
    freezer,
) -> None:
    freezer.move_to("2026-02-18 12:00:00+00:00")
    entry = make_entry(hass)
    await setup_entry(hass, entry)

    expected_last = datetime(2026, 2, 18, 12, 0, 0, tzinfo=UTC)
    expected_next = expected_last + timedelta(seconds=300)

    last_state = hass.states.get(get_entity_id(hass, "sensor", f"{MOCK_DOMAIN}_last_updated"))
    next_state = hass.states.get(get_entity_id(hass, "sensor", f"{MOCK_DOMAIN}_next_update"))
    assert last_state is not None
    assert next_state is not None
    assert datetime.fromisoformat(last_state.state) == expected_last
    assert datetime.fromisoformat(next_state.state) == expected_next
    assert next_state.state != "Refreshing"


async def test_entities_unavailable_after_failed_scheduled_poll(
    hass: HomeAssistant,
    mock_porkbun_client: AsyncMock,
) -> None:
    mock_porkbun_client.ping.side_effect = [MOCK_IPV4, TimeoutError(), TimeoutError()]
    entry = make_entry(hass)
    await setup_entry(hass, entry)

    entity_id = get_entity_id(hass, "sensor", f"{MOCK_DOMAIN}_last_updated")
    initial_state = hass.states.get(entity_id)
    assert initial_state is not None
    assert initial_state.state != "unavailable"

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=301))
    await hass.async_block_till_done()

    updated_state = hass.states.get(entity_id)
    assert updated_state is not None
    assert updated_state.state == "unavailable"


@pytest.mark.parametrize(
    ("expire_date", "expect_available"),
    [("2026-02-18 23:59:59", True), ("not-a-date", False)],
)
async def test_domain_expiry_sensor_values(
    hass: HomeAssistant,
    mock_porkbun_client: AsyncMock,
    expire_date: str,
    expect_available: bool,
) -> None:
    mock_porkbun_client.get_domain_info.return_value = DomainInfo(
        domain=MOCK_DOMAIN,
        status="ACTIVE",
        expire_date=expire_date,
        whois_privacy=True,
        auto_renew=True,
    )

    entry = make_entry(hass)
    await setup_entry(hass, entry)
    expiry_id = await enable_entity(hass, entry, "sensor", f"{MOCK_DOMAIN}_domain_expiry")

    state = hass.states.get(expiry_id)
    assert state is not None
    assert (state.state not in {"unknown", "unavailable"}) is expect_available
