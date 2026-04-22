"""DataUpdateCoordinator for Porkbun DDNS."""

from __future__ import annotations

from contextlib import suppress
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
    CONF_FAILURE_THRESHOLD,
    CONF_IPV4,
    CONF_IPV6,
    CONF_SECRET_KEY,
    CONF_STARTUP_DELAY,
    CONF_SUBDOMAINS,
    CONF_UPDATE_INTERVAL,
    DATA_FORCE_IMMEDIATE_REFRESH,
    DEFAULT_FAILURE_THRESHOLD,
    DEFAULT_STARTUP_DELAY,
    DEFAULT_TTL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    IPV6_DETECT_URL,
    LOGGER,
)


def _error_text(err: Exception) -> str:
    """Return a useful error string even for exceptions with an empty message."""
    return str(err) or type(err).__name__


@dataclass
class RecordState:
    """State for a single DNS record (subdomain + type)."""

    current_ip: str | None = None
    ok: bool = True
    error: str | None = None
    consecutive_failures: int = 0


@dataclass
class DdnsData:
    """Coordinator data for all tracked records."""

    public_ipv4: str | None = None
    public_ipv6: str | None = None
    records: dict[str, RecordState] = field(default_factory=dict)
    last_updated: datetime | None = None
    domain_info: DomainInfo | None = None


def _record_key(subdomain: str, record_type: str) -> str:
    """Generate a unique key for a record."""
    return f"{subdomain or '@'}_{record_type}"


class PorkbunDdnsCoordinator(DataUpdateCoordinator[DdnsData]):
    """Coordinator that manages DDNS updates for a single domain."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self._domain = str(config_entry.data[CONF_DOMAIN])

        interval = int(config_entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))
        self._startup_delay = max(0, int(config_entry.options.get(CONF_STARTUP_DELAY, DEFAULT_STARTUP_DELAY)))
        # One-shot bypass set by config/options/reauth flows after a successful ping.
        force_refresh: set[str] = hass.data.setdefault(DOMAIN, {}).setdefault(
            DATA_FORCE_IMMEDIATE_REFRESH, set()
        )
        if config_entry.entry_id in force_refresh:
            force_refresh.discard(config_entry.entry_id)
            self._startup_delay_until = datetime.now(tz=UTC)
        else:
            self._startup_delay_until = datetime.now(tz=UTC) + timedelta(seconds=self._startup_delay)
        self._failure_threshold = max(
            1, int(config_entry.options.get(CONF_FAILURE_THRESHOLD, DEFAULT_FAILURE_THRESHOLD))
        )

        super().__init__(
            hass,
            LOGGER,
            name=f"Porkbun DDNS ({self._domain})",
            config_entry=config_entry,
            update_interval=timedelta(seconds=interval),
            always_update=True,
        )
        self.data = DdnsData()
        self._startup_delay_logged = False
        self._consecutive_update_failures = 0
        self._last_ipv4: str | None = None
        self._last_ipv6: str | None = None
        self._client = PorkbunClient(
            async_get_clientsession(hass),
            str(config_entry.data[CONF_API_KEY]),
            str(config_entry.data[CONF_SECRET_KEY]),
        )

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
        subdomains = self.config_entry.options.get(CONF_SUBDOMAINS, [])
        if not isinstance(subdomains, list):
            return []
        return [subdomain for subdomain in subdomains if isinstance(subdomain, str)]

    @property
    def managed_records(self) -> list[str]:
        """Return all managed hostnames (root + configured subdomains)."""
        return [f"{sub}.{self._domain}" if sub else self._domain for sub in [""] + self.subdomains]

    @property
    def ipv4_enabled(self) -> bool:
        """Return whether IPv4 updates are enabled."""
        return bool(self.config_entry.options.get(CONF_IPV4, True))

    @property
    def ipv6_enabled(self) -> bool:
        """Return whether IPv6 updates are enabled."""
        return bool(self.config_entry.options.get(CONF_IPV6, False))

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

    @property
    def startup_delay_remaining(self) -> float:
        """Return seconds until the first update should run."""
        if self.data.last_updated is not None:
            return 0
        return max(0.0, (self._startup_delay_until - datetime.now(tz=UTC)).total_seconds())

    @property
    def startup_delay_until(self) -> datetime:
        """Return when the first update may run."""
        return self._startup_delay_until

    async def _async_update_data(self) -> DdnsData:
        """Fetch current IP and update DNS records if needed."""
        data = self.data
        issue_id = f"api_access_{self._domain}"
        try:
            # Optional startup delay (default 5 minutes) to avoid transient network/DNS issues
            # immediately after Home Assistant starts or the config entry reloads.
            now = datetime.now(tz=UTC)
            if data.last_updated is None and now < self._startup_delay_until:
                if not self._startup_delay_logged:
                    remaining = int((self._startup_delay_until - now).total_seconds())
                    LOGGER.debug(
                        "Startup delay active for %s; deferring first update for %ss",
                        self._domain,
                        remaining,
                    )
                    self._startup_delay_logged = True
                return data

            # Get current public IPs
            if self.ipv4_enabled:
                data.public_ipv4 = await self._client.ping()
                LOGGER.debug("Current public IPv4: %s", data.public_ipv4)

            if self.ipv6_enabled:
                data.public_ipv6 = await self._get_ipv6(async_get_clientsession(self.hass))
                LOGGER.debug("Current public IPv6: %s", data.public_ipv6)

            updates: list[tuple[str, str]] = []
            if self.ipv4_enabled and data.public_ipv4:
                updates.append(("A", data.public_ipv4))
            if self.ipv6_enabled and data.public_ipv6:
                updates.append(("AAAA", data.public_ipv6))

            # Determine if any IP has changed since the last successful cycle
            ip_changed = (self.ipv4_enabled and data.public_ipv4 != self._last_ipv4) or (
                self.ipv6_enabled and data.public_ipv6 != self._last_ipv6
            )

            for subdomain in ["", *self.subdomains]:
                for record_type, ip in updates:
                    await self._update_record(subdomain, record_type, ip, skip_fetch=not ip_changed)

            # Fetch domain registration info (non-critical, don't fail on error)
            with suppress(PorkbunApiError, aiohttp.ClientError, TimeoutError):
                data.domain_info = await self._client.get_domain_info(self._domain)

            if self._consecutive_update_failures:
                LOGGER.info(
                    "Porkbun DDNS (%s) recovered after %d failed update cycle(s)",
                    self._domain,
                    self._consecutive_update_failures,
                )
            self._consecutive_update_failures = 0
            self._last_ipv4 = data.public_ipv4
            self._last_ipv6 = data.public_ipv6
            data.last_updated = datetime.now(tz=UTC)
            ir.async_delete_issue(self.hass, DOMAIN, issue_id)
            return data

        except PorkbunAuthError as err:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN,
                translation_key="auth_failed",
            ) from err
        except (PorkbunApiError, aiohttp.ClientError, TimeoutError) as err:
            err_text = _error_text(err)
            self._consecutive_update_failures += 1
            update_log = (
                LOGGER.error if self._consecutive_update_failures >= self._failure_threshold else LOGGER.warning
            )
            update_log(
                "Porkbun DDNS (%s) update failed (%d consecutive failures): %s",
                self._domain,
                self._consecutive_update_failures,
                err_text,
            )
            # Domain-level failure (e.g. ping failed) — mark all records as failed
            for state in data.records.values():
                state.ok = False
                state.error = err_text
                state.consecutive_failures += 1

            # Below threshold: return stale data to keep entities available
            if self._consecutive_update_failures < self._failure_threshold:
                return data

            if isinstance(err, PorkbunApiError):
                ir.async_create_issue(
                    self.hass,
                    DOMAIN,
                    issue_id,
                    is_fixable=True,
                    is_persistent=False,
                    severity=ir.IssueSeverity.ERROR,
                    translation_key="api_access_disabled",
                    translation_placeholders={"domain": self._domain},
                    data={"entry_id": self.config_entry.entry_id},
                )
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_failed",
                translation_placeholders={"domain": self._domain, "error": err_text},
            ) from err

    async def _update_record(
        self,
        subdomain: str,
        record_type: str,
        target_ip: str,
        *,
        skip_fetch: bool = False,
    ) -> None:
        """Check and update a single DNS record if the IP has changed."""
        data = self.data
        key = _record_key(subdomain, record_type)
        state = data.records.setdefault(key, RecordState())
        label = f"{subdomain}.{self._domain}" if subdomain else self._domain

        try:
            if skip_fetch and state.current_ip is not None:
                # IP hasn't changed and we already know the record — skip the API call
                LOGGER.debug("%s %s record unchanged (skip_fetch), IP still %s", label, record_type, target_ip)
                state.ok = True
                state.error = None
                return

            existing = await self._client.get_records(self._domain, record_type, subdomain)
            current_ip = existing[0].content if existing else None

            if current_ip == target_ip:
                LOGGER.debug("%s %s record already correct (%s)", label, record_type, target_ip)
                state.current_ip = current_ip
                state.ok = True
                state.error = None
                return

            # IP differs — update or create
            if existing:
                LOGGER.info("Updating %s %s record: %s → %s", label, record_type, current_ip, target_ip)
                await self._client.edit_record_by_name_type(
                    self._domain, record_type, target_ip, subdomain, DEFAULT_TTL
                )
            else:
                LOGGER.info("Creating %s %s record: %s", label, record_type, target_ip)
                await self._client.create_record(self._domain, record_type, target_ip, subdomain, DEFAULT_TTL)

            if state.consecutive_failures:
                LOGGER.info(
                    "%s %s record recovered after %d consecutive failures",
                    label,
                    record_type,
                    state.consecutive_failures,
                )
            state.consecutive_failures = 0
            state.current_ip = target_ip
            state.ok = True
            state.error = None
        except (PorkbunApiError, aiohttp.ClientError, TimeoutError) as err:
            err_text = _error_text(err)
            state.consecutive_failures += 1
            update_log = LOGGER.error if state.consecutive_failures >= self._failure_threshold else LOGGER.warning
            update_log(
                "Failed to update %s %s (%d consecutive failures): %s",
                label,
                record_type,
                state.consecutive_failures,
                err_text,
            )
            state.ok = False
            state.error = err_text

    async def _get_ipv6(self, session: aiohttp.ClientSession) -> str | None:
        """Detect public IPv6 address via external service."""
        try:
            async with session.get(IPV6_DETECT_URL, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    return (await resp.text()).strip()
        except aiohttp.ClientError, TimeoutError:
            LOGGER.warning("Failed to detect IPv6 address; skipping IPv6 update")
        return None
