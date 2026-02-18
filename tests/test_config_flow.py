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
    DOMAIN,
)

from .conftest import MOCK_API_KEY, MOCK_DOMAIN, MOCK_IPV4, MOCK_SECRET_KEY, make_entry, setup_entry


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
    assert _parse_subdomains(raw) == expected


async def _start_user_flow(hass: HomeAssistant) -> str:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    return result["flow_id"]


async def _submit_user_step(
    hass: HomeAssistant,
    flow_id: str,
    *,
    api_key: str = MOCK_API_KEY,
    secret_key: str = MOCK_SECRET_KEY,
) -> config_entries.ConfigFlowResult:
    return await hass.config_entries.flow.async_configure(
        flow_id,
        {CONF_API_KEY: api_key, CONF_SECRET_KEY: secret_key},
    )


async def test_full_flow(hass: HomeAssistant) -> None:
    with patch("custom_components.porkbun_ddns.config_flow.PorkbunClient", autospec=True) as mock_cls:
        client = mock_cls.return_value
        client.ping = AsyncMock(return_value=MOCK_IPV4)
        client.get_records = AsyncMock(return_value=[])

        flow_id = await _start_user_flow(hass)
        result = await _submit_user_step(hass, flow_id)
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "domain"

        result = await hass.config_entries.flow.async_configure(
            flow_id,
            {CONF_DOMAIN: MOCK_DOMAIN, CONF_SUBDOMAINS: "www, vpn", CONF_IPV4: True, CONF_IPV6: False},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == MOCK_DOMAIN
    assert result["data"][CONF_API_KEY] == MOCK_API_KEY
    assert result["data"][CONF_DOMAIN] == MOCK_DOMAIN
    assert result["options"][CONF_SUBDOMAINS] == ["www", "vpn"]
    assert result["options"][CONF_IPV4] is True
    assert result["options"][CONF_IPV6] is False


@pytest.mark.parametrize(
    ("side_effect", "expected_error"),
    [
        (PorkbunAuthError("Invalid"), "invalid_auth"),
        (aiohttp.ClientConnectionError("Refused"), "cannot_connect"),
        (RuntimeError("boom"), "unknown"),
    ],
)
async def test_user_step_errors(
    hass: HomeAssistant,
    side_effect: Exception,
    expected_error: str,
) -> None:
    with patch("custom_components.porkbun_ddns.config_flow.PorkbunClient", autospec=True) as mock_cls:
        mock_cls.return_value.ping = AsyncMock(side_effect=side_effect)

        flow_id = await _start_user_flow(hass)
        result = await _submit_user_step(hass, flow_id)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": expected_error}


@pytest.mark.parametrize(
    ("side_effect", "expected_error"),
    [
        (PorkbunAuthError("Not found"), "domain_not_found"),
        (aiohttp.ClientConnectionError("Refused"), "cannot_connect"),
        (RuntimeError("boom"), "unknown"),
    ],
)
async def test_domain_step_errors(
    hass: HomeAssistant,
    side_effect: Exception,
    expected_error: str,
) -> None:
    with patch("custom_components.porkbun_ddns.config_flow.PorkbunClient", autospec=True) as mock_cls:
        client = mock_cls.return_value
        client.ping = AsyncMock(return_value=MOCK_IPV4)
        client.get_records = AsyncMock(side_effect=side_effect)

        flow_id = await _start_user_flow(hass)
        await _submit_user_step(hass, flow_id)
        result = await hass.config_entries.flow.async_configure(
            flow_id,
            {CONF_DOMAIN: MOCK_DOMAIN, CONF_IPV4: True, CONF_IPV6: False},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": expected_error}


async def test_duplicate_domain(hass: HomeAssistant) -> None:
    make_entry(hass)

    with patch("custom_components.porkbun_ddns.config_flow.PorkbunClient", autospec=True) as mock_cls:
        client = mock_cls.return_value
        client.ping = AsyncMock(return_value=MOCK_IPV4)
        client.get_records = AsyncMock(return_value=[])

        flow_id = await _start_user_flow(hass)
        await _submit_user_step(hass, flow_id)
        result = await hass.config_entries.flow.async_configure(
            flow_id,
            {CONF_DOMAIN: MOCK_DOMAIN, CONF_IPV4: True, CONF_IPV6: False},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.parametrize(
    ("side_effect", "expected_type", "expected_error"),
    [
        (None, FlowResultType.ABORT, None),
        (PorkbunAuthError("Invalid"), FlowResultType.FORM, "invalid_auth"),
        (aiohttp.ClientConnectionError("Refused"), FlowResultType.FORM, "cannot_connect"),
        (RuntimeError("boom"), FlowResultType.FORM, "unknown"),
    ],
)
async def test_reauth_flow(
    hass: HomeAssistant,
    mock_porkbun_client: AsyncMock,
    side_effect: Exception | None,
    expected_type: FlowResultType,
    expected_error: str | None,
) -> None:
    entry = make_entry(hass)
    await setup_entry(hass, entry)

    with patch("custom_components.porkbun_ddns.config_flow.PorkbunClient", autospec=True) as mock_cls:
        client = mock_cls.return_value
        client.ping = AsyncMock(side_effect=side_effect) if side_effect else AsyncMock(return_value=MOCK_IPV4)

        result = await entry.start_reauth_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: MOCK_API_KEY, CONF_SECRET_KEY: MOCK_SECRET_KEY},
        )

    assert result["type"] is expected_type
    if expected_type is FlowResultType.ABORT:
        assert result["reason"] == "reauth_successful"
        assert entry.data[CONF_API_KEY] == MOCK_API_KEY
        assert entry.data[CONF_SECRET_KEY] == MOCK_SECRET_KEY
    else:
        assert result["errors"] == {"base": expected_error}


async def test_options_flow_updates_and_reloads(
    hass: HomeAssistant,
    mock_porkbun_client: AsyncMock,
) -> None:
    entry = make_entry(hass, subdomains=["www"])
    await setup_entry(hass, entry)
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
    assert result["data"] == {
        CONF_SUBDOMAINS: ["www", "api"],
        CONF_IPV4: True,
        CONF_IPV6: True,
        CONF_UPDATE_INTERVAL: 600,
    }

    await hass.async_block_till_done()
    assert entry.runtime_data is not previous_coordinator
    assert entry.runtime_data.update_interval is not None
    assert entry.runtime_data.update_interval.total_seconds() == 600


@pytest.mark.parametrize(
    ("side_effect", "expected_type", "expected_error"),
    [
        (None, FlowResultType.ABORT, None),
        (PorkbunAuthError("Not found"), FlowResultType.FORM, "domain_not_found"),
        (aiohttp.ClientConnectionError("Refused"), FlowResultType.FORM, "cannot_connect"),
        (RuntimeError("boom"), FlowResultType.FORM, "unknown"),
    ],
)
async def test_reconfigure_flow(
    hass: HomeAssistant,
    mock_porkbun_client: AsyncMock,
    side_effect: Exception | None,
    expected_type: FlowResultType,
    expected_error: str | None,
) -> None:
    entry = make_entry(hass, subdomains=["www"])
    await setup_entry(hass, entry)

    with patch("custom_components.porkbun_ddns.config_flow.PorkbunClient", autospec=True) as mock_cls:
        client = mock_cls.return_value
        client.get_records = AsyncMock(side_effect=side_effect) if side_effect else AsyncMock(return_value=[])

        result = await entry.start_reconfigure_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_DOMAIN: MOCK_DOMAIN, CONF_SUBDOMAINS: "www, api", CONF_IPV4: True, CONF_IPV6: True},
        )

    assert result["type"] is expected_type
    if expected_type is FlowResultType.ABORT:
        assert result["reason"] == "reconfigure_successful"
    else:
        assert result["errors"] == {"base": expected_error}
