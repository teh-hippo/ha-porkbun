"""Tests for the DDNS coordinator."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.porkbun_ddns.api import (
    DnsRecord,
    PorkbunApiError,
    PorkbunAuthError,
)
from custom_components.porkbun_ddns.const import (
    CONF_IPV6,
    CONF_SUBDOMAINS,
    DOMAIN,
)
from custom_components.porkbun_ddns.coordinator import PorkbunDdnsCoordinator

from .conftest import MOCK_DOMAIN, MOCK_IPV4, MOCK_IPV6, make_entry


@pytest.fixture(autouse=True)
def _enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations."""


async def test_coordinator_creates_record_if_missing(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test coordinator creates a DNS record when none exists."""
    entry = make_entry(hass)
    coordinator = PorkbunDdnsCoordinator(hass, entry)

    data = await coordinator._async_update_data()

    assert data.public_ipv4 == MOCK_IPV4
    mock_porkbun_client.create_record.assert_called_once()
    record_state = data.records.get("@_A")
    assert record_state is not None
    assert record_state.current_ip == MOCK_IPV4


async def test_coordinator_skips_when_ip_matches(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test coordinator skips update when IP already matches."""
    mock_porkbun_client.get_records.return_value = [
        DnsRecord(id="123", name="example.com", record_type="A", content=MOCK_IPV4, ttl="600")
    ]
    entry = make_entry(hass)
    coordinator = PorkbunDdnsCoordinator(hass, entry)

    data = await coordinator._async_update_data()

    mock_porkbun_client.create_record.assert_not_called()
    mock_porkbun_client.edit_record_by_name_type.assert_not_called()
    assert data.records["@_A"].current_ip == MOCK_IPV4


async def test_coordinator_updates_when_ip_differs(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test coordinator updates record when IP has changed."""
    mock_porkbun_client.get_records.return_value = [
        DnsRecord(id="123", name="example.com", record_type="A", content="9.9.9.9", ttl="600")
    ]
    entry = make_entry(hass)
    coordinator = PorkbunDdnsCoordinator(hass, entry)

    data = await coordinator._async_update_data()

    mock_porkbun_client.edit_record_by_name_type.assert_called_once()
    assert data.records["@_A"].current_ip == MOCK_IPV4


async def test_coordinator_auth_error(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test coordinator raises ConfigEntryAuthFailed on auth error."""
    mock_porkbun_client.ping.side_effect = PorkbunAuthError("Invalid key")
    entry = make_entry(hass)
    coordinator = PorkbunDdnsCoordinator(hass, entry)

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


async def test_coordinator_api_error(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test coordinator raises UpdateFailed on API error."""
    mock_porkbun_client.ping.side_effect = PorkbunApiError("Server error")
    entry = make_entry(hass)
    coordinator = PorkbunDdnsCoordinator(hass, entry)

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_coordinator_with_subdomains(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test coordinator processes both root and subdomains."""
    entry = make_entry(hass, **{CONF_SUBDOMAINS: ["www", "vpn"]})
    coordinator = PorkbunDdnsCoordinator(hass, entry)

    data = await coordinator._async_update_data()

    # Should create records for root + www + vpn
    assert mock_porkbun_client.create_record.call_count == 3
    assert "@_A" in data.records
    assert "www_A" in data.records
    assert "vpn_A" in data.records


async def test_coordinator_domain_property(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test the domain property returns the configured domain."""
    entry = make_entry(hass)
    coordinator = PorkbunDdnsCoordinator(hass, entry)
    assert coordinator.domain == MOCK_DOMAIN


async def test_coordinator_record_count_no_data(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test record_count and ok_count return 0 with no records."""
    entry = make_entry(hass)
    coordinator = PorkbunDdnsCoordinator(hass, entry)
    # Before first update, data is empty
    assert coordinator.record_count == 0
    assert coordinator.ok_count == 0
    assert coordinator.all_ok is False


async def test_coordinator_ipv6_update(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test coordinator creates AAAA records when IPv6 is enabled."""
    entry = make_entry(hass, **{CONF_IPV6: True})
    coordinator = PorkbunDdnsCoordinator(hass, entry)

    # Mock _get_ipv6 to return an address
    with patch.object(coordinator, "_get_ipv6", return_value=MOCK_IPV6):
        data = await coordinator._async_update_data()

    assert data.public_ipv6 == MOCK_IPV6
    assert "@_AAAA" in data.records
    assert data.records["@_AAAA"].current_ip == MOCK_IPV6


async def test_coordinator_ipv6_detect_error(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test coordinator handles IPv6 detection failure gracefully."""
    entry = make_entry(hass, **{CONF_IPV6: True})
    coordinator = PorkbunDdnsCoordinator(hass, entry)

    # Mock _get_ipv6 to return None (detection failed)
    with patch.object(coordinator, "_get_ipv6", return_value=None):
        data = await coordinator._async_update_data()

    assert data.public_ipv6 is None
    # No AAAA record should be created
    assert "@_AAAA" not in data.records


async def test_coordinator_domain_info_fetch_error(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test coordinator handles domain info fetch failure gracefully."""
    mock_porkbun_client.get_domain_info.side_effect = PorkbunApiError("Not found")
    entry = make_entry(hass)
    coordinator = PorkbunDdnsCoordinator(hass, entry)

    data = await coordinator._async_update_data()

    # Should not fail — domain_info is non-critical
    assert data.domain_info is None
    assert data.public_ipv4 == MOCK_IPV4


async def test_coordinator_api_error_creates_issue(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test that PorkbunApiError creates a repair issue."""
    from homeassistant.helpers import issue_registry as ir

    mock_porkbun_client.ping.side_effect = PorkbunApiError("API disabled")
    entry = make_entry(hass)
    coordinator = PorkbunDdnsCoordinator(hass, entry)

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    issue_reg = ir.async_get(hass)
    issue = issue_reg.async_get_issue(DOMAIN, f"api_access_{MOCK_DOMAIN}")
    assert issue is not None


async def test_coordinator_record_update_failure(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test coordinator handles individual record update failure."""
    mock_porkbun_client.get_records.side_effect = PorkbunApiError("Record error")
    entry = make_entry(hass)
    coordinator = PorkbunDdnsCoordinator(hass, entry)

    data = await coordinator._async_update_data()

    record = data.records.get("@_A")
    assert record is not None
    assert record.ok is False
    assert record.error is not None


async def test_coordinator_network_timeout(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test coordinator raises UpdateFailed when the API times out."""
    mock_porkbun_client.ping.side_effect = TimeoutError()
    entry = make_entry(hass)
    coordinator = PorkbunDdnsCoordinator(hass, entry)

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_coordinator_network_connection_error(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test coordinator raises UpdateFailed on network connection failure."""
    mock_porkbun_client.ping.side_effect = aiohttp.ClientConnectionError("Network down")
    entry = make_entry(hass)
    coordinator = PorkbunDdnsCoordinator(hass, entry)

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_get_ipv6_success(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test _get_ipv6 returns the IPv6 address on success."""
    entry = make_entry(hass)
    coordinator = PorkbunDdnsCoordinator(hass, entry)

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.text = AsyncMock(return_value=MOCK_IPV6)
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=None)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_resp)

    result = await coordinator._get_ipv6(mock_session)
    assert result == MOCK_IPV6


async def test_coordinator_clears_issue_after_success(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test that a successful update clears a previously created API access issue."""
    from homeassistant.helpers import issue_registry as ir

    mock_porkbun_client.ping.side_effect = [PorkbunApiError("API disabled"), MOCK_IPV4]
    entry = make_entry(hass)
    coordinator = PorkbunDdnsCoordinator(hass, entry)

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    issue_reg = ir.async_get(hass)
    assert issue_reg.async_get_issue(DOMAIN, f"api_access_{MOCK_DOMAIN}") is not None

    await coordinator._async_update_data()

    assert issue_reg.async_get_issue(DOMAIN, f"api_access_{MOCK_DOMAIN}") is None


async def test_get_ipv6_failure(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test _get_ipv6 returns None on connection error."""
    entry = make_entry(hass)
    coordinator = PorkbunDdnsCoordinator(hass, entry)

    mock_session = MagicMock()
    mock_session.get = MagicMock(side_effect=aiohttp.ClientError("No IPv6"))

    result = await coordinator._get_ipv6(mock_session)
    assert result is None
