"""Async Porkbun API client."""

from __future__ import annotations

import asyncio
import secrets
from dataclasses import dataclass
from typing import Any

import aiohttp

from .const import (
    API_REQUEST_MAX_ATTEMPTS,
    API_REQUEST_RETRY_BASE,
    API_REQUEST_RETRY_JITTER_MAX,
    API_REQUEST_TIMEOUT,
    LOGGER,
    PORKBUN_API_BASE,
)


class PorkbunApiError(Exception):
    """Base exception for Porkbun API errors."""


class PorkbunAuthError(PorkbunApiError):
    """Authentication failure."""


@dataclass
class DnsRecord:
    """A DNS record from Porkbun."""

    id: str
    name: str
    record_type: str
    content: str
    ttl: str


@dataclass
class DomainInfo:
    """Domain registration info from Porkbun."""

    domain: str
    status: str
    expire_date: str
    whois_privacy: bool
    auto_renew: bool


class PorkbunClient:
    """Async client for the Porkbun API v3."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        api_key: str,
        secret_key: str,
        api_base: str = PORKBUN_API_BASE,
    ) -> None:
        """Initialize the client."""
        self._session = session
        self._api_key = api_key
        self._secret_key = secret_key
        self._api_base = api_base.rstrip("/")

    @staticmethod
    def _is_retryable_http_status(status_code: int) -> bool:
        """Return True for transient statuses that should be retried."""
        return status_code == 429 or status_code >= 500

    @staticmethod
    def _error_text(err: Exception) -> str:
        """Return a useful error string even when str(exception) is empty."""
        return str(err) or type(err).__name__

    async def _sleep_before_retry(self, attempt: int) -> None:
        """Sleep with exponential backoff and jitter before retrying."""
        delay = API_REQUEST_RETRY_BASE * (2 ** (attempt - 1))
        max_jitter_ms = max(1, int(API_REQUEST_RETRY_JITTER_MAX * 1000))
        delay += secrets.randbelow(max_jitter_ms + 1) / 1000
        await asyncio.sleep(delay)

    async def _request(self, endpoint: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a POST request to the Porkbun API."""
        url = f"{self._api_base}/{endpoint.lstrip('/')}"
        payload = {"apikey": self._api_key, "secretapikey": self._secret_key}
        if extra:
            payload.update(extra)

        timeout = aiohttp.ClientTimeout(total=API_REQUEST_TIMEOUT)
        for attempt in range(1, API_REQUEST_MAX_ATTEMPTS + 1):
            try:
                LOGGER.debug("Porkbun API request: POST %s (attempt %d/%d)", url, attempt, API_REQUEST_MAX_ATTEMPTS)
                async with self._session.post(url, json=payload, timeout=timeout) as resp:
                    try:
                        data: dict[str, Any] = await resp.json(content_type=None)
                    except ValueError as err:
                        body = (await resp.text()).strip().replace("\n", " ")
                        snippet = body[:200] if body else "<empty body>"
                        msg = f"Invalid API response (HTTP {resp.status}): {snippet}"
                        if attempt < API_REQUEST_MAX_ATTEMPTS and self._is_retryable_http_status(resp.status):
                            LOGGER.debug(
                                "Porkbun API transient response error, retrying (%d/%d): %s",
                                attempt,
                                API_REQUEST_MAX_ATTEMPTS,
                                msg,
                            )
                            await self._sleep_before_retry(attempt)
                            continue
                        raise PorkbunApiError(msg) from err

                    LOGGER.debug("Porkbun API response: %s %s", resp.status, data.get("status"))
                    status = data.get("status")
                    if resp.status == 403 or status != "SUCCESS":
                        msg = data.get("message") or (
                            "Unknown API error"
                            if resp.status == 403 or status == "ERROR"
                            else f"Unexpected status: {status}"
                        )
                        if "invalid api key" in msg.lower() or "invalid" in msg.lower():
                            raise PorkbunAuthError(msg)
                        if attempt < API_REQUEST_MAX_ATTEMPTS and self._is_retryable_http_status(resp.status):
                            LOGGER.debug(
                                "Porkbun API transient status error, retrying (%d/%d): HTTP %s %s",
                                attempt,
                                API_REQUEST_MAX_ATTEMPTS,
                                resp.status,
                                msg,
                            )
                            await self._sleep_before_retry(attempt)
                            continue
                        raise PorkbunApiError(msg)

                    return data
            except PorkbunAuthError:
                raise
            except (aiohttp.ClientError, TimeoutError) as err:
                if attempt >= API_REQUEST_MAX_ATTEMPTS:
                    raise
                LOGGER.debug(
                    "Porkbun API transient connection error, retrying (%d/%d): %s",
                    attempt,
                    API_REQUEST_MAX_ATTEMPTS,
                    self._error_text(err),
                )
                await self._sleep_before_retry(attempt)

        raise PorkbunApiError("Porkbun API request failed after retries")

    async def ping(self) -> str:
        """Validate credentials and return the caller's public IPv4 address."""
        return str((await self._request("ping"))["yourIp"])

    async def get_records(self, domain: str, record_type: str, subdomain: str = "") -> list[DnsRecord]:
        """Retrieve DNS records by domain, type, and optional subdomain."""
        endpoint = f"dns/retrieveByNameType/{domain}/{record_type}{f'/{subdomain}' if subdomain else ''}"
        try:
            data = await self._request(endpoint)
        except PorkbunApiError as err:
            if "no records" in str(err).lower() or "could not find" in str(err).lower():
                return []
            raise
        return [
            DnsRecord(
                id=r["id"],
                name=r["name"],
                record_type=r["type"],
                content=r["content"],
                ttl=r["ttl"],
            )
            for r in data.get("records", [])
        ]

    async def create_record(
        self,
        domain: str,
        record_type: str,
        content: str,
        subdomain: str = "",
        ttl: int = 600,
    ) -> str:
        """Create a DNS record. Returns the record ID."""
        extra: dict[str, Any] = {
            "type": record_type,
            "content": content,
            "ttl": str(ttl),
        }
        if subdomain:
            extra["name"] = subdomain
        data = await self._request(f"dns/create/{domain}", extra)
        return str(data.get("id", ""))

    async def edit_record_by_name_type(
        self,
        domain: str,
        record_type: str,
        content: str,
        subdomain: str = "",
        ttl: int = 600,
    ) -> None:
        """Edit DNS records matching domain, type, and optional subdomain."""
        endpoint = f"dns/editByNameType/{domain}/{record_type}{f'/{subdomain}' if subdomain else ''}"
        extra: dict[str, Any] = {"content": content, "ttl": str(ttl)}
        await self._request(endpoint, extra)

    async def get_domain_info(self, domain: str) -> DomainInfo | None:
        """Get domain registration info via domain/listAll."""
        data = await self._request("domain/listAll")
        for d in data.get("domains", []):
            if d.get("domain") == domain:
                return DomainInfo(
                    domain=d["domain"],
                    status=d.get("status", "UNKNOWN"),
                    expire_date=d.get("expireDate", ""),
                    whois_privacy=d.get("whoisPrivacy", "0") == "1",
                    auto_renew=d.get("autoRenew", "0") == "1",
                )
        return None
