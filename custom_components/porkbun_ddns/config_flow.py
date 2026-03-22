"""Config flow for Porkbun DDNS."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlowWithReload
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import PorkbunAuthError, PorkbunClient
from .const import (
    CONF_API_KEY,
    CONF_DOMAIN,
    CONF_FAILURE_THRESHOLD,
    CONF_IPV4,
    CONF_IPV6,
    CONF_SECRET_KEY,
    CONF_STARTUP_DELAY,
    CONF_SUBDOMAINS,
    CONF_UPDATE_INTERVAL,
    DEFAULT_FAILURE_THRESHOLD,
    DEFAULT_STARTUP_DELAY,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    LOGGER,
)

CONF_IGNORE_VERIFICATION = "ignore_verification"

STEP_CREDENTIALS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
        vol.Required(CONF_SECRET_KEY): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
    }
)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
        vol.Required(CONF_SECRET_KEY): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
        vol.Optional(CONF_IGNORE_VERIFICATION, default=False): bool,
    }
)

UPDATE_INTERVAL_SELECTOR = NumberSelector(NumberSelectorConfig(min=60, step=60, mode=NumberSelectorMode.BOX))
STARTUP_DELAY_SELECTOR = NumberSelector(NumberSelectorConfig(min=0, step=60, mode=NumberSelectorMode.BOX))
FAILURE_THRESHOLD_SELECTOR = NumberSelector(NumberSelectorConfig(min=1, max=10, step=1, mode=NumberSelectorMode.BOX))


def _domain_schema(
    *,
    domain_default: str = "",
    subdomains_default: str = "",
    ipv4_default: bool = True,
    ipv6_default: bool = False,
) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_DOMAIN, default=domain_default): str,
            vol.Optional(CONF_SUBDOMAINS, default=subdomains_default): str,
            vol.Optional(CONF_IPV4, default=ipv4_default): bool,
            vol.Optional(CONF_IPV6, default=ipv6_default): bool,
        }
    )


def _reconfigure_schema(
    *,
    api_key_default: str,
    domain_default: str,
    subdomains_default: str,
    ipv4_default: bool,
    ipv6_default: bool,
) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_API_KEY, default=api_key_default): str,
            vol.Required(CONF_SECRET_KEY): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
            vol.Required(CONF_DOMAIN, default=domain_default): str,
            vol.Optional(CONF_SUBDOMAINS, default=subdomains_default): str,
            vol.Optional(CONF_IPV4, default=ipv4_default): bool,
            vol.Optional(CONF_IPV6, default=ipv6_default): bool,
        }
    )


def _options_from_input(user_input: dict[str, Any], *, include_interval: bool = False) -> dict[str, Any]:
    options: dict[str, Any] = {
        CONF_SUBDOMAINS: _parse_subdomains(user_input.get(CONF_SUBDOMAINS, "")),
        CONF_IPV4: user_input.get(CONF_IPV4, True),
        CONF_IPV6: user_input.get(CONF_IPV6, False),
    }
    if include_interval:
        options[CONF_UPDATE_INTERVAL] = int(user_input.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))
        options[CONF_STARTUP_DELAY] = int(user_input.get(CONF_STARTUP_DELAY, DEFAULT_STARTUP_DELAY))
        options[CONF_FAILURE_THRESHOLD] = int(user_input.get(CONF_FAILURE_THRESHOLD, DEFAULT_FAILURE_THRESHOLD))
    return options


class PorkbunDdnsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Porkbun DDNS."""

    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._api_key: str = ""
        self._secret_key: str = ""
        self._skip_verification = False

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> PorkbunDdnsOptionsFlow:
        """Get the options flow handler."""
        return PorkbunDdnsOptionsFlow()

    async def _try_api(self, req: Awaitable[Any], auth_error: str = "invalid_auth") -> str | None:
        """Run an API call and return an error key, or None on success."""
        try:
            await req
        except PorkbunAuthError:
            return auth_error
        except aiohttp.ClientError, TimeoutError:
            return "cannot_connect"
        except Exception:
            LOGGER.exception("Unexpected error during API call")
            return "unknown"
        return None

    def _make_client(self, api_key: str, secret_key: str) -> PorkbunClient:
        """Create an API client with the given credentials."""
        return PorkbunClient(async_get_clientsession(self.hass), api_key, secret_key)

    async def _validate_domain(self, client: PorkbunClient, domain_name: str) -> str | None:
        return await self._try_api(client.get_records(domain_name, "A"), "domain_not_found")

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Step 1: Validate API credentials."""
        errors: dict[str, str] = {}
        if user_input is not None:
            ignore_verification = bool(user_input.get(CONF_IGNORE_VERIFICATION, False))
            client = self._make_client(user_input[CONF_API_KEY], user_input[CONF_SECRET_KEY])
            if error := await self._try_api(client.ping()):
                if not ignore_verification:
                    errors["base"] = error
                else:
                    self._api_key = user_input[CONF_API_KEY]
                    self._secret_key = user_input[CONF_SECRET_KEY]
                    self._skip_verification = True
                    return await self.async_step_domain()
            else:
                self._api_key = user_input[CONF_API_KEY]
                self._secret_key = user_input[CONF_SECRET_KEY]
                self._skip_verification = False
                return await self.async_step_domain()

        return self.async_show_form(step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors)

    async def async_step_domain(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Step 2: Configure domain and subdomains."""
        errors: dict[str, str] = {}
        schema = _domain_schema()

        if user_input is not None:
            domain_name = user_input[CONF_DOMAIN].strip().lower()

            await self.async_set_unique_id(domain_name)
            self._abort_if_unique_id_configured()

            if self._skip_verification:
                return self.async_create_entry(
                    title=domain_name,
                    data={
                        CONF_API_KEY: self._api_key,
                        CONF_SECRET_KEY: self._secret_key,
                        CONF_DOMAIN: domain_name,
                    },
                    options=_options_from_input(user_input, include_interval=True),
                )
            client = self._make_client(self._api_key, self._secret_key)
            if error := await self._validate_domain(client, domain_name):
                errors["base"] = error
            else:
                return self.async_create_entry(
                    title=domain_name,
                    data={
                        CONF_API_KEY: self._api_key,
                        CONF_SECRET_KEY: self._secret_key,
                        CONF_DOMAIN: domain_name,
                    },
                    options=_options_from_input(user_input, include_interval=True),
                )

        return self.async_show_form(step_id="domain", data_schema=schema, errors=errors)

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Handle re-authentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Confirm re-authentication with new credentials."""
        errors: dict[str, str] = {}

        if user_input is not None:
            client = self._make_client(user_input[CONF_API_KEY], user_input[CONF_SECRET_KEY])
            if error := await self._try_api(client.ping()):
                errors["base"] = error
            else:
                entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
                assert entry is not None

                self.hass.config_entries.async_update_entry(
                    entry,
                    data={
                        **entry.data,
                        CONF_API_KEY: user_input[CONF_API_KEY],
                        CONF_SECRET_KEY: user_input[CONF_SECRET_KEY],
                    },
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_CREDENTIALS_SCHEMA,
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle reconfiguration of domain settings."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        assert entry is not None
        current = entry.options
        schema = _reconfigure_schema(
            api_key_default=str(entry.data.get(CONF_API_KEY, "")),
            domain_default=str(entry.data.get(CONF_DOMAIN, "")),
            subdomains_default=", ".join(current.get(CONF_SUBDOMAINS, [])),
            ipv4_default=bool(current.get(CONF_IPV4, True)),
            ipv6_default=bool(current.get(CONF_IPV6, False)),
        )
        errors: dict[str, str] = {}

        if user_input is not None:
            domain_name = user_input[CONF_DOMAIN].strip().lower()
            api_key = str(user_input[CONF_API_KEY]).strip()
            secret_key = str(user_input[CONF_SECRET_KEY]).strip()
            client = self._make_client(api_key, secret_key)
            if error := await self._try_api(client.ping()):
                errors["base"] = error
            elif error := await self._validate_domain(client, domain_name):
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=domain_name,
                    title=domain_name,
                    data={
                        **entry.data,
                        CONF_API_KEY: api_key,
                        CONF_SECRET_KEY: secret_key,
                        CONF_DOMAIN: domain_name,
                    },
                    options={
                        **entry.options,
                        **_options_from_input(user_input),
                    },
                )

        return self.async_show_form(step_id="reconfigure", data_schema=schema, errors=errors)


class PorkbunDdnsOptionsFlow(OptionsFlowWithReload):
    """Handle options for Porkbun DDNS."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=_options_from_input(user_input, include_interval=True))

        current = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_UPDATE_INTERVAL,
                        default=current.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
                    ): UPDATE_INTERVAL_SELECTOR,
                    vol.Optional(
                        CONF_STARTUP_DELAY,
                        default=current.get(CONF_STARTUP_DELAY, DEFAULT_STARTUP_DELAY),
                    ): STARTUP_DELAY_SELECTOR,
                    vol.Optional(
                        CONF_FAILURE_THRESHOLD,
                        default=current.get(CONF_FAILURE_THRESHOLD, DEFAULT_FAILURE_THRESHOLD),
                    ): FAILURE_THRESHOLD_SELECTOR,
                    vol.Optional(
                        CONF_SUBDOMAINS,
                        default=", ".join(current.get(CONF_SUBDOMAINS, [])),
                    ): str,
                    vol.Optional(CONF_IPV4, default=current.get(CONF_IPV4, True)): bool,
                    vol.Optional(CONF_IPV6, default=current.get(CONF_IPV6, False)): bool,
                }
            ),
        )


def _parse_subdomains(raw: str) -> list[str]:
    """Parse a comma-separated subdomain string into a clean list."""
    return [s.strip().lower() for s in raw.split(",") if s.strip()]
