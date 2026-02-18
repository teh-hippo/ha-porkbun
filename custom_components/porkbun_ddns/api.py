"""Async Porkbun API client."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import aiohttp

from .const import LOGGER, PORKBUN_API_BASE, API_REQUEST_TIMEOUT


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

    def _auth_body(self) -> dict[str, str]:
        """Return the authentication payload."""
        return {"apikey": self._api_key, "secretapikey": self._secret_key}

    async def _request(self, endpoint: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a POST request to the Porkbun API."""
        url = f"{self._api_base}/{endpoint.lstrip('/')}"
        payload = self._auth_body()
        if extra:
            payload.update(extra)

        LOGGER.debug("Porkbun API request: POST %s", url)
        async with self._session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=API_REQUEST_TIMEOUT)) as resp:
            data: dict[str, Any] = await resp.json(content_type=None)
            LOGGER.debug("Porkbun API response: %s %s", resp.status, data.get("status"))

            if resp.status == 403 or data.get("status") == "ERROR":
                msg = data.get("message", "Unknown API error")
                if "Invalid API key" in msg or "invalid" in msg.lower():
                    raise PorkbunAuthError(msg)
                raise PorkbunApiError(msg)

            if data.get("status") != "SUCCESS":
                raise PorkbunApiError(data.get("message", f"Unexpected status: {data.get('status')}"))

            return data

    async def ping(self) -> str:
        """Validate credentials and return the caller's public IPv4 address."""
        data = await self._request("ping")
        your_ip: str = data["yourIp"]
        return your_ip

    async def get_records(self, domain: str, record_type: str, subdomain: str = "") -> list[DnsRecord]:
        """Retrieve DNS records by domain, type, and optional subdomain."""
        endpoint = f"dns/retrieveByNameType/{domain}/{record_type}"
        if subdomain:
            endpoint += f"/{subdomain}"
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
        endpoint = f"dns/editByNameType/{domain}/{record_type}"
        if subdomain:
            endpoint += f"/{subdomain}"
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
