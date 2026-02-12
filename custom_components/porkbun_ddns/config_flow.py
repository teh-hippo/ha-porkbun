"""Config flow for Porkbun DDNS."""

from __future__ import annotations

from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PorkbunAuthError, PorkbunClient
from .const import (
    CONF_API_KEY,
    CONF_DOMAIN,
    CONF_IPV4,
    CONF_IPV6,
    CONF_SECRET_KEY,
    CONF_SUBDOMAINS,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    LOGGER,
)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
        vol.Required(CONF_SECRET_KEY): str,
    }
)

STEP_DOMAIN_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DOMAIN): str,
        vol.Optional(CONF_SUBDOMAINS, default=""): str,
        vol.Optional(CONF_IPV4, default=True): bool,
        vol.Optional(CONF_IPV6, default=False): bool,
    }
)


class PorkbunDdnsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Porkbun DDNS."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._api_key: str = ""
        self._secret_key: str = ""

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> PorkbunDdnsOptionsFlow:
        """Get the options flow handler."""
        return PorkbunDdnsOptionsFlow(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Step 1: Validate API credentials."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                session = async_get_clientsession(self.hass)
                client = PorkbunClient(session, user_input[CONF_API_KEY], user_input[CONF_SECRET_KEY])
                await client.ping()
            except PorkbunAuthError:
                errors["base"] = "invalid_auth"
            except (aiohttp.ClientError, TimeoutError):
                errors["base"] = "cannot_connect"
            except Exception:
                LOGGER.exception("Unexpected error during credential validation")
                errors["base"] = "unknown"
            else:
                self._api_key = user_input[CONF_API_KEY]
                self._secret_key = user_input[CONF_SECRET_KEY]
                return await self.async_step_domain()

        return self.async_show_form(step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors)

    async def async_step_domain(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Step 2: Configure domain and subdomains."""
        errors: dict[str, str] = {}

        if user_input is not None:
            domain_name = user_input[CONF_DOMAIN].strip().lower()
            subdomains = _parse_subdomains(user_input.get(CONF_SUBDOMAINS, ""))

            await self.async_set_unique_id(domain_name)
            self._abort_if_unique_id_configured()

            # Validate domain is accessible with these keys
            try:
                session = async_get_clientsession(self.hass)
                client = PorkbunClient(session, self._api_key, self._secret_key)
                await client.get_records(domain_name, "A")
            except PorkbunAuthError:
                errors["base"] = "domain_not_found"
            except (aiohttp.ClientError, TimeoutError):
                errors["base"] = "cannot_connect"
            except Exception:
                LOGGER.exception("Unexpected error during domain validation")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=domain_name,
                    data={
                        CONF_API_KEY: self._api_key,
                        CONF_SECRET_KEY: self._secret_key,
                        CONF_DOMAIN: domain_name,
                    },
                    options={
                        CONF_SUBDOMAINS: subdomains,
                        CONF_IPV4: user_input.get(CONF_IPV4, True),
                        CONF_IPV6: user_input.get(CONF_IPV6, False),
                        CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
                    },
                )

        return self.async_show_form(step_id="domain", data_schema=STEP_DOMAIN_SCHEMA, errors=errors)

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Handle re-authentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Confirm re-authentication with new credentials."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                session = async_get_clientsession(self.hass)
                client = PorkbunClient(session, user_input[CONF_API_KEY], user_input[CONF_SECRET_KEY])
                await client.ping()
            except PorkbunAuthError:
                errors["base"] = "invalid_auth"
            except (aiohttp.ClientError, TimeoutError):
                errors["base"] = "cannot_connect"
            except Exception:
                LOGGER.exception("Unexpected error during re-authentication")
                errors["base"] = "unknown"
            else:
                entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
                if entry:
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
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )


class PorkbunDdnsOptionsFlow(OptionsFlow):
    """Handle options for Porkbun DDNS."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            subdomains = _parse_subdomains(user_input.get(CONF_SUBDOMAINS, ""))
            return self.async_create_entry(
                data={
                    CONF_SUBDOMAINS: subdomains,
                    CONF_IPV4: user_input.get(CONF_IPV4, True),
                    CONF_IPV6: user_input.get(CONF_IPV6, False),
                    CONF_UPDATE_INTERVAL: user_input.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
                }
            )

        current = self._config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_UPDATE_INTERVAL,
                        default=current.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
                    ): vol.All(vol.Coerce(int), vol.Range(min=60)),
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
