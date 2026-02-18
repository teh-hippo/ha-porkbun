"""Tests for binary sensors."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.porkbun_ddns.api import DomainInfo, PorkbunApiError
from custom_components.porkbun_ddns.const import CONF_SUBDOMAINS

from .conftest import MOCK_DOMAIN, enable_entity, get_entity_id, make_entry, setup_entry


@pytest.mark.parametrize(
    ("inject_failure", "expected_state", "summary_prefix", "has_failed_records"),
    [
        (False, "off", "2/2", False),
        (True, "on", "1/2", True),
    ],
)
async def test_health_sensor_states(
    hass: HomeAssistant,
    mock_porkbun_client: AsyncMock,
    inject_failure: bool,
    expected_state: str,
    summary_prefix: str,
    has_failed_records: bool,
) -> None:
    if inject_failure:
        call_count = 0

        async def _get_records(domain: str, record_type: str, subdomain: str = "") -> list[object]:
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise PorkbunApiError("DNS error")
            return []

        mock_porkbun_client.get_records.side_effect = _get_records

    entry = make_entry(hass, **{CONF_SUBDOMAINS: ["www"]})
    await setup_entry(hass, entry)

    state = hass.states.get(get_entity_id(hass, "binary_sensor", f"{MOCK_DOMAIN}_health"))
    assert state is not None
    assert state.state == expected_state
    assert state.attributes["summary"].startswith(summary_prefix)
    assert state.attributes["managed_subdomains"] == ["@", "www"]
    assert len(state.attributes["record_status"]) == 2
    assert ("failed_records" in state.attributes) is has_failed_records


async def test_whois_privacy_sensor_disabled_by_default(
    hass: HomeAssistant,
    mock_porkbun_client: AsyncMock,
) -> None:
    entry = make_entry(hass)
    await setup_entry(hass, entry)

    entity_id = get_entity_id(hass, "binary_sensor", f"{MOCK_DOMAIN}_whois_privacy")
    entity_entry = er.async_get(hass).async_get(entity_id)
    assert entity_entry is not None
    assert entity_entry.disabled_by is not None


async def test_whois_privacy_sensor_value(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    mock_porkbun_client.get_domain_info.return_value = DomainInfo(
        domain=MOCK_DOMAIN,
        status="ACTIVE",
        expire_date="2026-02-18 23:59:59",
        whois_privacy=True,
        auto_renew=True,
    )

    entry = make_entry(hass)
    await setup_entry(hass, entry)
    entity_id = await enable_entity(hass, entry, "binary_sensor", f"{MOCK_DOMAIN}_whois_privacy")

    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "on"
