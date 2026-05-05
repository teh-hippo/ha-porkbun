"""Tests for the config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import aiohttp
import pytest
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType, InvalidData

from custom_components.porkbun_ddns.api import PorkbunAuthError
from custom_components.porkbun_ddns.config_flow import CONF_IGNORE_VERIFICATION, _parse_subdomains
from custom_components.porkbun_ddns.const import (
    CONF_API_KEY,
    CONF_DOMAIN,
    CONF_FAILURE_THRESHOLD,
    CONF_IPV4,
    CONF_IPV6,
    CONF_MANAGE_ROOT,
    CONF_SECRET_KEY,
    CONF_STARTUP_DELAY,
    CONF_SUBDOMAINS,
    CONF_UPDATE_INTERVAL,
    DEFAULT_FAILURE_THRESHOLD,
    DEFAULT_STARTUP_DELAY,
    DEFAULT_UPDATE_INTERVAL,
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
    ignore_verification: bool = False,
) -> config_entries.ConfigFlowResult:
    payload: dict[str, str | bool] = {CONF_API_KEY: api_key, CONF_SECRET_KEY: secret_key}
    if ignore_verification:
        payload[CONF_IGNORE_VERIFICATION] = True
    return await hass.config_entries.flow.async_configure(
        flow_id,
        payload,
    )


def _schema_keys(schema: vol.Schema) -> set[str]:
    return {str(getattr(key, "schema", key)) for key in schema.schema}


async def test_user_step_schema_has_ignore_verification(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert CONF_IGNORE_VERIFICATION in _schema_keys(result["data_schema"])


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
    assert result["options"][CONF_UPDATE_INTERVAL] == DEFAULT_UPDATE_INTERVAL
    assert result["options"][CONF_STARTUP_DELAY] == DEFAULT_STARTUP_DELAY
    assert result["options"][CONF_FAILURE_THRESHOLD] == DEFAULT_FAILURE_THRESHOLD


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


async def test_user_step_error_can_be_ignored_for_now(hass: HomeAssistant) -> None:
    with patch("custom_components.porkbun_ddns.config_flow.PorkbunClient", autospec=True) as mock_cls:
        client = mock_cls.return_value
        client.ping = AsyncMock(side_effect=PorkbunAuthError("Invalid"))
        client.get_records = AsyncMock(return_value=[])

        flow_id = await _start_user_flow(hass)
        first = await _submit_user_step(hass, flow_id)
        assert first["type"] is FlowResultType.FORM
        assert first["step_id"] == "user"
        assert first["errors"] == {"base": "invalid_auth"}

        second = await _submit_user_step(hass, flow_id, ignore_verification=True)

    assert second["type"] is FlowResultType.FORM
    assert second["step_id"] == "domain"


async def test_domain_step_skips_domain_validation_after_ignored_user_verification(
    hass: HomeAssistant,
) -> None:
    with patch("custom_components.porkbun_ddns.config_flow.PorkbunClient", autospec=True) as mock_cls:
        client = mock_cls.return_value
        client.ping = AsyncMock(side_effect=PorkbunAuthError("Invalid"))
        client.get_records = AsyncMock(side_effect=RuntimeError("should not be called"))

        flow_id = await _start_user_flow(hass)
        await _submit_user_step(hass, flow_id, ignore_verification=True)
        result = await hass.config_entries.flow.async_configure(
            flow_id,
            {CONF_DOMAIN: MOCK_DOMAIN, CONF_SUBDOMAINS: "www, vpn", CONF_IPV4: True, CONF_IPV6: False},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_API_KEY] == MOCK_API_KEY
    assert result["data"][CONF_SECRET_KEY] == MOCK_SECRET_KEY
    assert client.get_records.await_count == 0


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


async def test_reauth_schema_excludes_ignore_verification(
    hass: HomeAssistant,
    mock_porkbun_client: AsyncMock,
) -> None:
    entry = make_entry(hass)
    await setup_entry(hass, entry)

    result = await entry.start_reauth_flow(hass)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    schema_keys = _schema_keys(result["data_schema"])
    assert CONF_IGNORE_VERIFICATION not in schema_keys
    assert {CONF_API_KEY, CONF_SECRET_KEY}.issubset(schema_keys)


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
            CONF_STARTUP_DELAY: 300,
            CONF_FAILURE_THRESHOLD: 5,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_SUBDOMAINS: ["www", "api"],
        CONF_MANAGE_ROOT: True,
        CONF_IPV4: True,
        CONF_IPV6: True,
        CONF_UPDATE_INTERVAL: 600,
        CONF_STARTUP_DELAY: 300,
        CONF_FAILURE_THRESHOLD: 5,
    }

    await hass.async_block_till_done()
    assert entry.runtime_data is not previous_coordinator
    assert entry.runtime_data.update_interval is not None
    assert entry.runtime_data.update_interval.total_seconds() == 600


async def test_full_flow_with_manage_root_disabled(hass: HomeAssistant) -> None:
    """The domain step accepts manage_root=False as long as a subdomain is configured."""
    with patch("custom_components.porkbun_ddns.config_flow.PorkbunClient", autospec=True) as mock_cls:
        client = mock_cls.return_value
        client.ping = AsyncMock(return_value=MOCK_IPV4)
        client.get_records = AsyncMock(return_value=[])

        flow_id = await _start_user_flow(hass)
        await _submit_user_step(hass, flow_id)
        result = await hass.config_entries.flow.async_configure(
            flow_id,
            {
                CONF_DOMAIN: MOCK_DOMAIN,
                CONF_SUBDOMAINS: "www",
                CONF_MANAGE_ROOT: False,
                CONF_IPV4: True,
                CONF_IPV6: False,
            },
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["options"][CONF_MANAGE_ROOT] is False
    assert result["options"][CONF_SUBDOMAINS] == ["www"]


async def test_domain_step_rejects_no_records_combination(hass: HomeAssistant) -> None:
    """manage_root=False with no subdomains is rejected with at_least_one_record."""
    with patch("custom_components.porkbun_ddns.config_flow.PorkbunClient", autospec=True) as mock_cls:
        client = mock_cls.return_value
        client.ping = AsyncMock(return_value=MOCK_IPV4)
        client.get_records = AsyncMock(side_effect=RuntimeError("should not be called"))

        flow_id = await _start_user_flow(hass)
        await _submit_user_step(hass, flow_id)
        result = await hass.config_entries.flow.async_configure(
            flow_id,
            {
                CONF_DOMAIN: MOCK_DOMAIN,
                CONF_SUBDOMAINS: "",
                CONF_MANAGE_ROOT: False,
                CONF_IPV4: True,
                CONF_IPV6: False,
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "domain"
    assert result["errors"] == {"base": "at_least_one_record"}
    assert client.get_records.await_count == 0
    schema = result["data_schema"]
    assert schema is not None
    schema_defaults = {
        str(getattr(key, "schema", key)): key.default() if callable(getattr(key, "default", None)) else None
        for key in schema.schema
    }
    assert schema_defaults[CONF_MANAGE_ROOT] is False
    assert schema_defaults[CONF_DOMAIN] == MOCK_DOMAIN


async def test_options_flow_accepts_manage_root_disabled_with_subdomains(
    hass: HomeAssistant,
    mock_porkbun_client: AsyncMock,
) -> None:
    entry = make_entry(hass, subdomains=["www"])
    await setup_entry(hass, entry)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_SUBDOMAINS: "www",
            CONF_MANAGE_ROOT: False,
            CONF_IPV4: True,
            CONF_IPV6: False,
            CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
            CONF_STARTUP_DELAY: DEFAULT_STARTUP_DELAY,
            CONF_FAILURE_THRESHOLD: DEFAULT_FAILURE_THRESHOLD,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_MANAGE_ROOT] is False
    assert result["data"][CONF_SUBDOMAINS] == ["www"]


async def test_options_flow_rejects_no_records_combination(
    hass: HomeAssistant,
    mock_porkbun_client: AsyncMock,
) -> None:
    entry = make_entry(hass, subdomains=["www"])
    await setup_entry(hass, entry)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_SUBDOMAINS: "",
            CONF_MANAGE_ROOT: False,
            CONF_IPV4: True,
            CONF_IPV6: False,
            CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
            CONF_STARTUP_DELAY: DEFAULT_STARTUP_DELAY,
            CONF_FAILURE_THRESHOLD: DEFAULT_FAILURE_THRESHOLD,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    assert result["errors"] == {"base": "at_least_one_record"}
    # The just-rejected user input must come back as the form defaults rather than
    # the entry's saved options, otherwise the user has to re-enter their changes.
    schema = result["data_schema"]
    assert schema is not None
    schema_defaults = {
        str(getattr(key, "schema", key)): key.default() if callable(getattr(key, "default", None)) else None
        for key in schema.schema
    }
    assert schema_defaults[CONF_MANAGE_ROOT] is False
    assert schema_defaults[CONF_SUBDOMAINS] == ""


@pytest.mark.parametrize(
    ("ping_side_effect", "records_side_effect", "expected_type", "expected_error"),
    [
        (None, None, FlowResultType.ABORT, None),
        (PorkbunAuthError("Invalid"), None, FlowResultType.FORM, "invalid_auth"),
        (aiohttp.ClientConnectionError("Refused"), None, FlowResultType.FORM, "cannot_connect"),
        (RuntimeError("boom"), None, FlowResultType.FORM, "unknown"),
        (None, PorkbunAuthError("Not found"), FlowResultType.FORM, "domain_not_found"),
    ],
)
async def test_reconfigure_flow(
    hass: HomeAssistant,
    mock_porkbun_client: AsyncMock,
    ping_side_effect: Exception | None,
    records_side_effect: Exception | None,
    expected_type: FlowResultType,
    expected_error: str | None,
) -> None:
    entry = make_entry(hass, subdomains=["www"])
    await setup_entry(hass, entry)
    new_api_key = "pk1_reconfigure_new"
    new_secret_key = "sk1_reconfigure_new"

    with patch("custom_components.porkbun_ddns.config_flow.PorkbunClient", autospec=True) as mock_cls:
        client = mock_cls.return_value
        client.ping = AsyncMock(side_effect=ping_side_effect) if ping_side_effect else AsyncMock(return_value=MOCK_IPV4)
        client.get_records = (
            AsyncMock(side_effect=records_side_effect) if records_side_effect else AsyncMock(return_value=[])
        )

        result = await entry.start_reconfigure_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_API_KEY: new_api_key,
                CONF_SECRET_KEY: new_secret_key,
                CONF_DOMAIN: MOCK_DOMAIN,
            },
        )

    assert result["type"] is expected_type
    assert client.ping.await_count == 1
    if expected_type is FlowResultType.ABORT:
        assert result["reason"] == "reconfigure_successful"
        assert entry.data[CONF_API_KEY] == new_api_key
        assert entry.data[CONF_SECRET_KEY] == new_secret_key
    else:
        assert result["errors"] == {"base": expected_error}
        if ping_side_effect is not None:
            assert client.get_records.await_count == 0


async def test_reconfigure_flow_requires_secret_key(
    hass: HomeAssistant,
    mock_porkbun_client: AsyncMock,
) -> None:
    entry = make_entry(hass, subdomains=["www"])
    await setup_entry(hass, entry)

    with patch("custom_components.porkbun_ddns.config_flow.PorkbunClient", autospec=True) as mock_cls:
        client = mock_cls.return_value
        client.ping = AsyncMock(return_value=MOCK_IPV4)
        client.get_records = AsyncMock(return_value=[])

        result = await entry.start_reconfigure_flow(hass)
        with pytest.raises(InvalidData):
            await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_API_KEY: MOCK_API_KEY,
                    CONF_DOMAIN: MOCK_DOMAIN,
                },
            )

    assert entry.data[CONF_SECRET_KEY] == MOCK_SECRET_KEY
    assert client.ping.await_count == 0
