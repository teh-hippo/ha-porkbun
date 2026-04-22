"""Tests for the DDNS coordinator."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.porkbun_ddns.api import DnsRecord, PorkbunApiError, PorkbunAuthError
from custom_components.porkbun_ddns.const import (
    CONF_FAILURE_THRESHOLD,
    CONF_IPV6,
    CONF_STARTUP_DELAY,
    CONF_SUBDOMAINS,
    DOMAIN,
)
from custom_components.porkbun_ddns.coordinator import PorkbunDdnsCoordinator

from .conftest import MOCK_DOMAIN, MOCK_IPV4, MOCK_IPV6, make_entry


@pytest.mark.parametrize(
    ("existing_ip", "expected_create", "expected_edit", "expected_current"),
    [
        (None, 1, 0, MOCK_IPV4),
        (MOCK_IPV4, 0, 0, MOCK_IPV4),
        ("9.9.9.9", 0, 1, MOCK_IPV4),
    ],
)
async def test_record_sync_paths(
    hass: HomeAssistant,
    mock_porkbun_client: AsyncMock,
    existing_ip: str | None,
    expected_create: int,
    expected_edit: int,
    expected_current: str,
) -> None:
    if existing_ip is not None:
        mock_porkbun_client.get_records.return_value = [
            DnsRecord(id="123", name=MOCK_DOMAIN, record_type="A", content=existing_ip, ttl="600"),
        ]

    data = await PorkbunDdnsCoordinator(hass, make_entry(hass))._async_update_data()

    assert mock_porkbun_client.create_record.call_count == expected_create
    assert mock_porkbun_client.edit_record_by_name_type.call_count == expected_edit
    assert data.records["@_A"].current_ip == expected_current


@pytest.mark.parametrize(
    ("side_effect", "expected_exception"),
    [
        (PorkbunAuthError("Invalid key"), ConfigEntryAuthFailed),
        (PorkbunApiError("Server error"), UpdateFailed),
        (TimeoutError(), UpdateFailed),
        (aiohttp.ClientConnectionError("Network down"), UpdateFailed),
    ],
)
async def test_coordinator_error_handling(
    hass: HomeAssistant,
    mock_porkbun_client: AsyncMock,
    side_effect: Exception,
    expected_exception: type[Exception],
) -> None:
    mock_porkbun_client.ping.side_effect = side_effect
    # Auth errors raise immediately; transient errors only raise after exceeding threshold
    coordinator = PorkbunDdnsCoordinator(hass, make_entry(hass, **{CONF_FAILURE_THRESHOLD: 1}))
    with pytest.raises(expected_exception):
        await coordinator._async_update_data()


async def test_coordinator_updatefailed_includes_error_for_empty_exception_message(
    hass: HomeAssistant,
    mock_porkbun_client: AsyncMock,
) -> None:
    """Ensure UpdateFailed has a useful error placeholder when str(exception) is empty."""
    mock_porkbun_client.ping.side_effect = TimeoutError()

    with pytest.raises(UpdateFailed) as exc:
        await PorkbunDdnsCoordinator(hass, make_entry(hass, **{CONF_FAILURE_THRESHOLD: 1}))._async_update_data()

    placeholders = getattr(exc.value, "translation_placeholders", None) or {}
    assert placeholders.get("error") == "TimeoutError"


async def test_startup_delay_defers_first_update(
    hass: HomeAssistant,
    mock_porkbun_client: AsyncMock,
    freezer,
) -> None:
    freezer.move_to("2026-02-18 12:00:00+00:00")
    coordinator = PorkbunDdnsCoordinator(hass, make_entry(hass, **{CONF_STARTUP_DELAY: 300}))

    data = await coordinator._async_update_data()
    assert data.last_updated is None
    assert mock_porkbun_client.ping.call_count == 0

    freezer.move_to("2026-02-18 12:05:01+00:00")
    data = await coordinator._async_update_data()
    assert data.public_ipv4 == MOCK_IPV4
    assert mock_porkbun_client.ping.call_count == 1


async def test_coordinator_subdomains_and_counters(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    coordinator = PorkbunDdnsCoordinator(hass, make_entry(hass, **{CONF_SUBDOMAINS: ["www", "vpn"]}))

    assert coordinator.domain == MOCK_DOMAIN
    assert coordinator.record_count == 0
    assert coordinator.ok_count == 0
    assert coordinator.all_ok is False

    data = await coordinator._async_update_data()

    assert mock_porkbun_client.create_record.call_count == 3
    assert set(data.records) == {"@_A", "www_A", "vpn_A"}


@pytest.mark.parametrize("detected_ipv6", [MOCK_IPV6, None])
async def test_coordinator_ipv6_paths(
    hass: HomeAssistant,
    mock_porkbun_client: AsyncMock,
    detected_ipv6: str | None,
) -> None:
    coordinator = PorkbunDdnsCoordinator(hass, make_entry(hass, **{CONF_IPV6: True}))

    with patch.object(coordinator, "_get_ipv6", return_value=detected_ipv6):
        data = await coordinator._async_update_data()

    assert data.public_ipv6 == detected_ipv6
    assert ("@_AAAA" in data.records) is (detected_ipv6 is not None)


async def test_coordinator_domain_info_fetch_error(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    mock_porkbun_client.get_domain_info.side_effect = PorkbunApiError("Not found")

    data = await PorkbunDdnsCoordinator(hass, make_entry(hass))._async_update_data()

    assert data.domain_info is None
    assert data.public_ipv4 == MOCK_IPV4


async def test_coordinator_issue_lifecycle(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    mock_porkbun_client.ping.side_effect = [PorkbunApiError("API disabled"), MOCK_IPV4]
    entry = make_entry(hass, **{CONF_FAILURE_THRESHOLD: 1})
    coordinator = PorkbunDdnsCoordinator(hass, entry)

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    issue_id = f"api_access_{MOCK_DOMAIN}"
    issue_reg = ir.async_get(hass)
    issue = issue_reg.async_get_issue(DOMAIN, issue_id)
    assert issue is not None
    assert issue.is_fixable is True
    assert issue.data == {"entry_id": entry.entry_id}

    await coordinator._async_update_data()
    assert issue_reg.async_get_issue(DOMAIN, issue_id) is None


async def test_coordinator_record_update_failure_marks_record(
    hass: HomeAssistant,
    mock_porkbun_client: AsyncMock,
) -> None:
    mock_porkbun_client.get_records.side_effect = PorkbunApiError("Record error")

    record = (await PorkbunDdnsCoordinator(hass, make_entry(hass))._async_update_data()).records["@_A"]
    assert record.ok is False
    assert record.error is not None


async def test_coordinator_escalates_domain_failure_logging(
    hass: HomeAssistant,
    mock_porkbun_client: AsyncMock,
) -> None:
    mock_porkbun_client.ping.side_effect = [TimeoutError(), TimeoutError(), TimeoutError()]
    coordinator = PorkbunDdnsCoordinator(hass, make_entry(hass))

    with patch("custom_components.porkbun_ddns.coordinator.LOGGER") as logger:
        # First two failures are below threshold — return stale data, no raise
        await coordinator._async_update_data()
        await coordinator._async_update_data()
        # Third failure hits threshold — raises UpdateFailed
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()

    assert logger.warning.call_count >= 2
    assert any("update failed" in str(call.args[0]).lower() for call in logger.error.call_args_list)


async def test_coordinator_record_failure_escalates_and_recovers(
    hass: HomeAssistant,
    mock_porkbun_client: AsyncMock,
) -> None:
    mock_porkbun_client.get_records.side_effect = [
        PorkbunApiError("Record error"),
        PorkbunApiError("Record error"),
        PorkbunApiError("Record error"),
        [],
    ]
    coordinator = PorkbunDdnsCoordinator(hass, make_entry(hass))

    with patch("custom_components.porkbun_ddns.coordinator.LOGGER") as logger:
        await coordinator._async_update_data()
        await coordinator._async_update_data()
        await coordinator._async_update_data()
        await coordinator._async_update_data()

    assert any("failed to update" in str(call.args[0]).lower() for call in logger.error.call_args_list)
    assert any("recovered after" in str(call.args[0]).lower() for call in logger.info.call_args_list)
    assert coordinator.data.records["@_A"].consecutive_failures == 0


async def test_get_ipv6_success(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value=MOCK_IPV6)
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    session = MagicMock()
    session.get = MagicMock(return_value=mock_response)

    result = await PorkbunDdnsCoordinator(hass, make_entry(hass))._get_ipv6(session)
    assert result == MOCK_IPV6


async def test_get_ipv6_failure(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    session = MagicMock()
    session.get = MagicMock(side_effect=aiohttp.ClientError("No IPv6"))

    assert await PorkbunDdnsCoordinator(hass, make_entry(hass))._get_ipv6(session) is None


async def test_graceful_degradation_returns_stale_data(
    hass: HomeAssistant,
    mock_porkbun_client: AsyncMock,
) -> None:
    """Transient failures below threshold return stale data instead of raising."""
    coordinator = PorkbunDdnsCoordinator(hass, make_entry(hass))

    # First call succeeds — establishes baseline data
    data = await coordinator._async_update_data()
    assert data.public_ipv4 == MOCK_IPV4
    assert data.last_updated is not None
    first_updated = data.last_updated

    # Second call fails — below threshold, returns stale data
    mock_porkbun_client.ping.side_effect = TimeoutError()
    data = await coordinator._async_update_data()
    assert data.public_ipv4 == MOCK_IPV4
    assert data.last_updated == first_updated  # unchanged, stale
    assert coordinator._consecutive_update_failures == 1


async def test_skip_fetch_when_ip_unchanged(
    hass: HomeAssistant,
    mock_porkbun_client: AsyncMock,
) -> None:
    """When IP hasn't changed, skip_fetch avoids redundant get_records calls."""
    coordinator = PorkbunDdnsCoordinator(hass, make_entry(hass))

    # First call — IP is new, get_records is called
    await coordinator._async_update_data()
    first_get_records_count = mock_porkbun_client.get_records.call_count

    # Second call — same IP, get_records should be skipped
    await coordinator._async_update_data()
    assert mock_porkbun_client.get_records.call_count == first_get_records_count
