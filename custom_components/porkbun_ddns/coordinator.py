"""DataUpdateCoordinator for Porkbun DDNS."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from functools import cached_property

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import DomainInfo, PorkbunApiError, PorkbunAuthError, PorkbunClient
from .const import (
    CONF_API_KEY,
    CONF_DOMAIN,
    CONF_IPV4,
    CONF_IPV6,
    CONF_SECRET_KEY,
    CONF_SUBDOMAINS,
    CONF_UPDATE_INTERVAL,
    DEFAULT_TTL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    IPV6_DETECT_URL,
    LOGGER,
)


@dataclass
class RecordState:
    """State for a single DNS record (subdomain + type)."""

    current_ip: str | None = None
    ok: bool = True
    error: str | None = None


@dataclass
class DdnsData:
    """Coordinator data for all tracked records."""

    public_ipv4: str | None = None
    public_ipv6: str | None = None
    records: dict[str, RecordState] = field(default_factory=dict)
    last_updated: datetime | None = None
    domain_info: DomainInfo | None = None

    def record_key(self, subdomain: str, record_type: str) -> str:
        """Generate a unique key for a record."""
        return f"{subdomain or '@'}_{record_type}"


class PorkbunDdnsCoordinator(DataUpdateCoordinator[DdnsData]):
    """Coordinator that manages DDNS updates for a single domain."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self._domain = config_entry.data[CONF_DOMAIN]
        self._api_key = config_entry.data[CONF_API_KEY]
        self._secret_key = config_entry.data[CONF_SECRET_KEY]

        interval = config_entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)

        super().__init__(
            hass,
            LOGGER,
            name=f"Porkbun DDNS ({self._domain})",
            config_entry=config_entry,
            update_interval=timedelta(seconds=interval),
            always_update=True,
        )
        self.data = DdnsData()
        self._client = PorkbunClient(async_get_clientsession(hass), self._api_key, self._secret_key)

    @property
    def domain(self) -> str:
        """Return the domain name."""
        return self._domain

    @cached_property
    def device_info(self) -> DeviceInfo:
        """Return shared device info for all entities under this domain."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._domain)},
            name=self._domain,
            manufacturer="Porkbun",
            model="DDNS",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://porkbun.com/account/domains",
        )

    @property
    def subdomains(self) -> list[str]:
        """Return configured subdomains."""
        return self.config_entry.options.get(CONF_SUBDOMAINS, [])  # type: ignore[return-value]

    @property
    def ipv4_enabled(self) -> bool:
        """Return whether IPv4 updates are enabled."""
        return self.config_entry.options.get(CONF_IPV4, True)  # type: ignore[return-value]

    @property
    def ipv6_enabled(self) -> bool:
        """Return whether IPv6 updates are enabled."""
        return self.config_entry.options.get(CONF_IPV6, False)  # type: ignore[return-value]

    @property
    def record_count(self) -> int:
        """Return total number of tracked records."""
        return len(self.data.records)

    @property
    def ok_count(self) -> int:
        """Return number of records that updated successfully."""
        return sum(1 for r in self.data.records.values() if r.ok)

    @property
    def all_ok(self) -> bool:
        """Return True if all records updated successfully."""
        return self.record_count > 0 and self.ok_count == self.record_count

    async def _async_update_data(self) -> DdnsData:
        """Fetch current IP and update DNS records if needed."""
        data = self.data
        try:
            session = async_get_clientsession(self.hass)
            client = self._client

            # Get current public IPs
            if self.ipv4_enabled:
                data.public_ipv4 = await client.ping()
                LOGGER.debug("Current public IPv4: %s", data.public_ipv4)

            if self.ipv6_enabled:
                data.public_ipv6 = await self._get_ipv6(session)
                LOGGER.debug("Current public IPv6: %s", data.public_ipv6)

            # Update records for root domain + each subdomain
            targets = [""] + self.subdomains
            for subdomain in targets:
                if self.ipv4_enabled and data.public_ipv4:
                    await self._update_record(
                        client,
                        data,
                        subdomain,
                        "A",
                        data.public_ipv4,
                    )
                if self.ipv6_enabled and data.public_ipv6:
                    await self._update_record(
                        client,
                        data,
                        subdomain,
                        "AAAA",
                        data.public_ipv6,
                    )

            # Fetch domain registration info (non-critical, don't fail on error)
            try:
                data.domain_info = await client.get_domain_info(self._domain)
            except (PorkbunApiError, aiohttp.ClientError, TimeoutError):
                LOGGER.debug("Failed to fetch domain info for %s", self._domain)

            data.last_updated = datetime.now(tz=UTC)
            ir.async_delete_issue(self.hass, DOMAIN, f"api_access_{self._domain}")
            return data

        except PorkbunAuthError as err:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN,
                translation_key="auth_failed",
            ) from err
        except (PorkbunApiError, aiohttp.ClientError, TimeoutError) as err:
            # Domain-level failure (e.g. ping failed) — mark all records as failed
            for state in data.records.values():
                state.ok = False
                state.error = str(err)
            if isinstance(err, PorkbunApiError):
                ir.async_create_issue(
                    self.hass,
                    DOMAIN,
                    f"api_access_{self._domain}",
                    is_fixable=False,
                    is_persistent=False,
                    severity=ir.IssueSeverity.ERROR,
                    translation_key="api_access_disabled",
                    translation_placeholders={"domain": self._domain},
                )
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_failed",
                translation_placeholders={"domain": self._domain, "error": str(err)},
            ) from err

    async def _update_record(
        self,
        client: PorkbunClient,
        data: DdnsData,
        subdomain: str,
        record_type: str,
        target_ip: str,
    ) -> None:
        """Check and update a single DNS record if the IP has changed."""
        key = data.record_key(subdomain, record_type)
        state = data.records.get(key, RecordState())
        label = f"{subdomain}.{self._domain}" if subdomain else self._domain

        try:
            existing = await client.get_records(self._domain, record_type, subdomain)
            current_ip = existing[0].content if existing else None

            if current_ip == target_ip:
                LOGGER.debug("%s %s record already correct (%s)", label, record_type, target_ip)
                state.current_ip = current_ip
                state.ok = True
                state.error = None
                data.records[key] = state
                return

            # IP differs — update or create
            if existing:
                LOGGER.info("Updating %s %s record: %s → %s", label, record_type, current_ip, target_ip)
                await client.edit_record_by_name_type(self._domain, record_type, target_ip, subdomain, DEFAULT_TTL)
            else:
                LOGGER.info("Creating %s %s record: %s", label, record_type, target_ip)
                await client.create_record(self._domain, record_type, target_ip, subdomain, DEFAULT_TTL)

            state.current_ip = target_ip
            state.ok = True
            state.error = None
        except (PorkbunApiError, aiohttp.ClientError, TimeoutError) as err:
            LOGGER.warning("Failed to update %s %s: %s", label, record_type, err)
            state.ok = False
            state.error = str(err)

        data.records[key] = state

    async def _get_ipv6(self, session: aiohttp.ClientSession) -> str | None:
        """Detect public IPv6 address via external service."""
        try:
            async with session.get(IPV6_DETECT_URL, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    return (await resp.text()).strip()
        except (aiohttp.ClientError, TimeoutError):
            LOGGER.warning("Failed to detect IPv6 address; skipping IPv6 update")
        return None
