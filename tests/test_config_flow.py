"""Tests for the config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.porkbun_ddns.const import (
    CONF_API_KEY,
    CONF_DOMAIN,
    CONF_IPV4,
    CONF_IPV6,
    CONF_SECRET_KEY,
    CONF_SUBDOMAINS,
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
    from custom_components.porkbun_ddns.api import PorkbunAuthError

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
    import aiohttp

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
