"""Tests for the config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import aiohttp
import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.porkbun_ddns.api import PorkbunAuthError
from custom_components.porkbun_ddns.config_flow import _parse_subdomains
from custom_components.porkbun_ddns.const import (
    CONF_API_KEY,
    CONF_DOMAIN,
    CONF_IPV4,
    CONF_IPV6,
    CONF_SECRET_KEY,
    CONF_SUBDOMAINS,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)

from .conftest import MOCK_API_KEY, MOCK_DOMAIN, MOCK_IPV4, MOCK_SECRET_KEY


@pytest.fixture(autouse=True)
def _enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations in tests."""


@pytest.fixture
def mock_ping():
    """Mock a successful ping."""
    with patch(
        "custom_components.porkbun_ddns.config_flow.PorkbunClient",
        autospec=True,
    ) as mock_cls:
        client = mock_cls.return_value
        client.ping = AsyncMock(return_value=MOCK_IPV4)
        client.get_records = AsyncMock(return_value=[])
        yield client


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("", []),
        ("www", ["www"]),
        (" www, VPN ", ["www", "vpn"]),
        ("a,, b, ,c", ["a", "b", "c"]),
        (",, ,", []),
    ],
)
def test_parse_subdomains_cases(raw: str, expected: list[str]) -> None:
    """Test _parse_subdomains handles common edge cases."""
    assert _parse_subdomains(raw) == expected


# --- User step tests ---


async def test_full_flow(hass: HomeAssistant, mock_ping: AsyncMock) -> None:
    """Test a successful two-step config flow."""
    # Step 1: Credentials
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_KEY: MOCK_API_KEY, CONF_SECRET_KEY: MOCK_SECRET_KEY},
    )

    # Step 2: Domain
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "domain"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_DOMAIN: MOCK_DOMAIN, CONF_SUBDOMAINS: "www, vpn", CONF_IPV4: True, CONF_IPV6: False},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == MOCK_DOMAIN
    assert result["data"][CONF_API_KEY] == MOCK_API_KEY
    assert result["data"][CONF_DOMAIN] == MOCK_DOMAIN
    assert result["options"][CONF_SUBDOMAINS] == ["www", "vpn"]
    assert result["options"][CONF_IPV4] is True
    assert result["options"][CONF_IPV6] is False


async def test_invalid_auth(hass: HomeAssistant) -> None:
    """Test config flow with invalid credentials."""
    with patch(
        "custom_components.porkbun_ddns.config_flow.PorkbunClient",
        autospec=True,
    ) as mock_cls:
        mock_cls.return_value.ping = AsyncMock(side_effect=PorkbunAuthError("Invalid"))

        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "bad_key", CONF_SECRET_KEY: "bad_secret"},
        )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "invalid_auth"}


async def test_connection_error(hass: HomeAssistant) -> None:
    """Test config flow with connection error."""
    with patch(
        "custom_components.porkbun_ddns.config_flow.PorkbunClient",
        autospec=True,
    ) as mock_cls:
        mock_cls.return_value.ping = AsyncMock(side_effect=aiohttp.ClientConnectionError("Refused"))

        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: MOCK_API_KEY, CONF_SECRET_KEY: MOCK_SECRET_KEY},
        )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "cannot_connect"}


async def test_user_step_unknown_error(hass: HomeAssistant) -> None:
    """Test config flow with unexpected exception."""
    with patch(
        "custom_components.porkbun_ddns.config_flow.PorkbunClient",
        autospec=True,
    ) as mock_cls:
        mock_cls.return_value.ping = AsyncMock(side_effect=RuntimeError("boom"))

        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: MOCK_API_KEY, CONF_SECRET_KEY: MOCK_SECRET_KEY},
        )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "unknown"}


# --- Domain step error tests ---


async def test_domain_step_not_found(hass: HomeAssistant) -> None:
    """Test domain step when domain is not accessible."""
    with patch(
        "custom_components.porkbun_ddns.config_flow.PorkbunClient",
        autospec=True,
    ) as mock_cls:
        client = mock_cls.return_value
        client.ping = AsyncMock(return_value=MOCK_IPV4)
        client.get_records = AsyncMock(side_effect=PorkbunAuthError("Not found"))

        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: MOCK_API_KEY, CONF_SECRET_KEY: MOCK_SECRET_KEY},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_DOMAIN: MOCK_DOMAIN, CONF_IPV4: True, CONF_IPV6: False},
        )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "domain_not_found"}


async def test_domain_step_connect_error(hass: HomeAssistant) -> None:
    """Test domain step with connection error."""
    with patch(
        "custom_components.porkbun_ddns.config_flow.PorkbunClient",
        autospec=True,
    ) as mock_cls:
        client = mock_cls.return_value
        client.ping = AsyncMock(return_value=MOCK_IPV4)
        client.get_records = AsyncMock(side_effect=aiohttp.ClientConnectionError("Refused"))

        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: MOCK_API_KEY, CONF_SECRET_KEY: MOCK_SECRET_KEY},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_DOMAIN: MOCK_DOMAIN, CONF_IPV4: True, CONF_IPV6: False},
        )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "cannot_connect"}


async def test_domain_step_unknown_error(hass: HomeAssistant) -> None:
    """Test domain step with unexpected exception."""
    with patch(
        "custom_components.porkbun_ddns.config_flow.PorkbunClient",
        autospec=True,
    ) as mock_cls:
        client = mock_cls.return_value
        client.ping = AsyncMock(return_value=MOCK_IPV4)
        client.get_records = AsyncMock(side_effect=RuntimeError("boom"))

        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: MOCK_API_KEY, CONF_SECRET_KEY: MOCK_SECRET_KEY},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_DOMAIN: MOCK_DOMAIN, CONF_IPV4: True, CONF_IPV6: False},
        )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "unknown"}


async def test_duplicate_domain(hass: HomeAssistant, mock_ping: AsyncMock) -> None:
    """Test that duplicate domains are rejected."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCK_DOMAIN,
        data={CONF_API_KEY: MOCK_API_KEY, CONF_SECRET_KEY: MOCK_SECRET_KEY, CONF_DOMAIN: MOCK_DOMAIN},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_KEY: MOCK_API_KEY, CONF_SECRET_KEY: MOCK_SECRET_KEY},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_DOMAIN: MOCK_DOMAIN, CONF_IPV4: True, CONF_IPV6: False},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


# --- Reauth flow tests ---


async def test_reauth_flow_success(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test successful re-authentication flow."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCK_DOMAIN,
        data={CONF_API_KEY: "old_key", CONF_SECRET_KEY: "old_secret", CONF_DOMAIN: MOCK_DOMAIN},
        options={CONF_SUBDOMAINS: [], CONF_IPV4: True, CONF_IPV6: False, CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    with patch(
        "custom_components.porkbun_ddns.config_flow.PorkbunClient",
        autospec=True,
    ) as mock_cls:
        mock_cls.return_value.ping = AsyncMock(return_value=MOCK_IPV4)

        result = await entry.start_reauth_flow(hass)
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "reauth_confirm"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: MOCK_API_KEY, CONF_SECRET_KEY: MOCK_SECRET_KEY},
        )

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "reauth_successful"
        assert entry.data[CONF_API_KEY] == MOCK_API_KEY
        assert entry.data[CONF_SECRET_KEY] == MOCK_SECRET_KEY


async def test_reauth_flow_invalid_auth(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test re-authentication with invalid credentials."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCK_DOMAIN,
        data={CONF_API_KEY: "old_key", CONF_SECRET_KEY: "old_secret", CONF_DOMAIN: MOCK_DOMAIN},
        options={CONF_SUBDOMAINS: [], CONF_IPV4: True, CONF_IPV6: False, CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    with patch(
        "custom_components.porkbun_ddns.config_flow.PorkbunClient",
        autospec=True,
    ) as mock_cls:
        mock_cls.return_value.ping = AsyncMock(side_effect=PorkbunAuthError("Invalid"))

        result = await entry.start_reauth_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "bad_key", CONF_SECRET_KEY: "bad_secret"},
        )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "invalid_auth"}


async def test_reauth_flow_connect_error(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test re-authentication with connection error."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCK_DOMAIN,
        data={CONF_API_KEY: "old_key", CONF_SECRET_KEY: "old_secret", CONF_DOMAIN: MOCK_DOMAIN},
        options={CONF_SUBDOMAINS: [], CONF_IPV4: True, CONF_IPV6: False, CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    with patch(
        "custom_components.porkbun_ddns.config_flow.PorkbunClient",
        autospec=True,
    ) as mock_cls:
        mock_cls.return_value.ping = AsyncMock(side_effect=aiohttp.ClientConnectionError("Refused"))

        result = await entry.start_reauth_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: MOCK_API_KEY, CONF_SECRET_KEY: MOCK_SECRET_KEY},
        )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "cannot_connect"}


async def test_reauth_flow_unknown_error(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test re-authentication with unexpected exception."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCK_DOMAIN,
        data={CONF_API_KEY: "old_key", CONF_SECRET_KEY: "old_secret", CONF_DOMAIN: MOCK_DOMAIN},
        options={CONF_SUBDOMAINS: [], CONF_IPV4: True, CONF_IPV6: False, CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    with patch(
        "custom_components.porkbun_ddns.config_flow.PorkbunClient",
        autospec=True,
    ) as mock_cls:
        mock_cls.return_value.ping = AsyncMock(side_effect=RuntimeError("boom"))

        result = await entry.start_reauth_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: MOCK_API_KEY, CONF_SECRET_KEY: MOCK_SECRET_KEY},
        )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "unknown"}


# --- Options flow tests ---


async def test_options_flow(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test the options flow."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCK_DOMAIN,
        data={CONF_API_KEY: MOCK_API_KEY, CONF_SECRET_KEY: MOCK_SECRET_KEY, CONF_DOMAIN: MOCK_DOMAIN},
        options={
            CONF_SUBDOMAINS: ["www"],
            CONF_IPV4: True,
            CONF_IPV6: False,
            CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_SUBDOMAINS: "www, api",
            CONF_IPV4: True,
            CONF_IPV6: True,
            CONF_UPDATE_INTERVAL: 600,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_SUBDOMAINS] == ["www", "api"]
    assert result["data"][CONF_IPV4] is True
    assert result["data"][CONF_IPV6] is True
    assert result["data"][CONF_UPDATE_INTERVAL] == 600


async def test_options_flow_triggers_reload(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test options flow automatically reloads the entry."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCK_DOMAIN,
        data={CONF_API_KEY: MOCK_API_KEY, CONF_SECRET_KEY: MOCK_SECRET_KEY, CONF_DOMAIN: MOCK_DOMAIN},
        options={
            CONF_SUBDOMAINS: ["www"],
            CONF_IPV4: True,
            CONF_IPV6: False,
            CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    previous_coordinator = entry.runtime_data

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_SUBDOMAINS: "www, api",
            CONF_IPV4: True,
            CONF_IPV6: True,
            CONF_UPDATE_INTERVAL: 600,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY

    await hass.async_block_till_done()

    assert entry.runtime_data is not previous_coordinator
    assert entry.runtime_data.update_interval is not None
    assert entry.runtime_data.update_interval.total_seconds() == 600


# --- Reconfigure flow tests ---


async def test_reconfigure_flow(hass: HomeAssistant, mock_porkbun_client: AsyncMock) -> None:
    """Test successful reconfiguration flow."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCK_DOMAIN,
        data={CONF_API_KEY: MOCK_API_KEY, CONF_SECRET_KEY: MOCK_SECRET_KEY, CONF_DOMAIN: MOCK_DOMAIN},
        options={
            CONF_SUBDOMAINS: ["www"],
            CONF_IPV4: True,
            CONF_IPV6: False,
            CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    with patch(
        "custom_components.porkbun_ddns.config_flow.PorkbunClient",
        autospec=True,
    ) as mock_cls:
        mock_cls.return_value.get_records = AsyncMock(return_value=[])

        result = await entry.start_reconfigure_flow(hass)
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "reconfigure"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_DOMAIN: MOCK_DOMAIN, CONF_SUBDOMAINS: "www, api", CONF_IPV4: True, CONF_IPV6: True},
        )

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "reconfigure_successful"


@pytest.mark.parametrize(
    ("side_effect", "expected_error"),
    [
        (PorkbunAuthError("Not found"), "domain_not_found"),
        (aiohttp.ClientConnectionError("Refused"), "cannot_connect"),
        (RuntimeError("boom"), "unknown"),
    ],
)
async def test_reconfigure_flow_errors(
    hass: HomeAssistant, mock_porkbun_client: AsyncMock, side_effect: Exception, expected_error: str
) -> None:
    """Test reconfigure flow error handling paths."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCK_DOMAIN,
        data={CONF_API_KEY: MOCK_API_KEY, CONF_SECRET_KEY: MOCK_SECRET_KEY, CONF_DOMAIN: MOCK_DOMAIN},
        options={
            CONF_SUBDOMAINS: ["www"],
            CONF_IPV4: True,
            CONF_IPV6: False,
            CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    with patch(
        "custom_components.porkbun_ddns.config_flow.PorkbunClient",
        autospec=True,
    ) as mock_cls:
        mock_cls.return_value.get_records = AsyncMock(side_effect=side_effect)

        result = await entry.start_reconfigure_flow(hass)
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "reconfigure"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_DOMAIN: MOCK_DOMAIN, CONF_SUBDOMAINS: "www, api", CONF_IPV4: True, CONF_IPV6: True},
        )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": expected_error}
