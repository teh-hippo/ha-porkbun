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

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        http_status: int | None = None,
        request_id: str | None = None,
        next_action: dict[str, Any] | None = None,
        retryable: bool = False,
        retry_after: float | None = None,
    ) -> None:
        """Initialize a Porkbun API error with structured response metadata."""
        super().__init__(message)
        self.code = code
        self.http_status = http_status
        self.request_id = request_id
        self.next_action = next_action
        self.retryable = retryable
        self.retry_after = retry_after


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


def _api_bool(value: object) -> bool:
    """Normalize Porkbun boolean fields returned as strings, numbers, or booleans."""
    return str(value).lower() in {"1", "true", "yes", "on"}


class PorkbunClient:
    """Async client for the Porkbun API v3."""

    _AUTH_ERROR_CODES = {
        "API_KEY_REQUIRED",
        "INVALID_API_KEYS_001",
        "INVALID_API_KEYS_002",
        "INVALID_TOKEN",
        "INVALID_USER",
        "MISSING_APIKEY",
        "MISSING_SECRETAPIKEY",
    }
    _NO_RECORD_CODES = {
        "DNS_RECORD_NOT_FOUND",
        "NO_RECORDS_FOUND",
        "RECORD_NOT_FOUND",
    }

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

    async def _sleep_before_retry(self, attempt: int, retry_after: float | None = None) -> None:
        """Sleep with exponential backoff and jitter before retrying."""
        if retry_after is not None:
            await asyncio.sleep(max(0.0, retry_after))
            return
        delay = API_REQUEST_RETRY_BASE * (2 ** (attempt - 1))
        max_jitter_ms = max(1, int(API_REQUEST_RETRY_JITTER_MAX * 1000))
        delay += secrets.randbelow(max_jitter_ms + 1) / 1000
        await asyncio.sleep(delay)

    @staticmethod
    def _response_header(response: aiohttp.ClientResponse, name: str) -> str | None:
        """Return a response header when it contains a scalar value."""
        value = response.headers.get(name)
        if isinstance(value, str):
            return value
        return None

    @classmethod
    def _error_from_response(
        cls,
        data: dict[str, Any],
        response: aiohttp.ClientResponse,
    ) -> PorkbunApiError:
        """Build a typed API error from Porkbun response metadata."""
        code_value = data.get("code")
        code = str(code_value) if code_value is not None else None
        message_value = data.get("message")
        message = str(message_value) if message_value else f"Unexpected status: {data.get('status')}"
        request_id_value = data.get("requestId")
        request_id = (
            str(request_id_value) if request_id_value is not None else cls._response_header(response, "X-Request-Id")
        )
        next_action_value = data.get("next_action")
        next_action = next_action_value if isinstance(next_action_value, dict) else None
        retryable_value = next_action.get("retryable") if next_action is not None else None
        retryable = (
            retryable_value if isinstance(retryable_value, bool) else cls._is_retryable_http_status(response.status)
        )

        retry_after: float | None = None
        retry_after_header = cls._response_header(response, "Retry-After")
        if retry_after_header is not None:
            try:
                retry_after = float(retry_after_header)
            except ValueError:
                retry_after = None

        error_type: type[PorkbunApiError] = PorkbunApiError
        if code in cls._AUTH_ERROR_CODES or (code is None and "invalid api key" in message.lower()):
            error_type = PorkbunAuthError

        return error_type(
            message,
            code=code,
            http_status=response.status,
            request_id=request_id,
            next_action=next_action,
            retryable=retryable,
            retry_after=retry_after,
        )

    async def _request(
        self,
        endpoint: str,
        extra: dict[str, Any] | None = None,
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Make a POST request to the Porkbun API."""
        url = f"{self._api_base}/{endpoint.lstrip('/')}"
        payload = {"apikey": self._api_key, "secretapikey": self._secret_key}
        if extra:
            payload.update(extra)
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key is not None else None

        timeout = aiohttp.ClientTimeout(total=API_REQUEST_TIMEOUT)
        for attempt in range(1, API_REQUEST_MAX_ATTEMPTS + 1):
            try:
                LOGGER.debug("Porkbun API request: POST %s (attempt %d/%d)", url, attempt, API_REQUEST_MAX_ATTEMPTS)
                async with self._session.post(url, json=payload, timeout=timeout, headers=headers) as resp:
                    parse_error: Exception | None = None
                    try:
                        parsed = await resp.json(content_type=None)
                    except ValueError as json_error:
                        parsed = None
                        parse_error = json_error

                    if not isinstance(parsed, dict):
                        body = (await resp.text()).strip().replace("\n", " ")
                        snippet = body[:200] if body else "<empty body>"
                        response_error = PorkbunApiError(
                            f"Invalid API response (HTTP {resp.status}): {snippet}",
                            http_status=resp.status,
                            request_id=self._response_header(resp, "X-Request-Id"),
                            retryable=self._is_retryable_http_status(resp.status),
                        )
                        if attempt < API_REQUEST_MAX_ATTEMPTS and self._is_retryable_http_status(resp.status):
                            LOGGER.debug(
                                "Porkbun API transient response error, retrying (%d/%d): %s",
                                attempt,
                                API_REQUEST_MAX_ATTEMPTS,
                                response_error,
                            )
                            await self._sleep_before_retry(attempt)
                            continue
                        raise response_error from parse_error

                    data: dict[str, Any] = parsed
                    LOGGER.debug("Porkbun API response: %s %s", resp.status, data.get("status"))
                    status = data.get("status")
                    if status != "SUCCESS":
                        api_error = self._error_from_response(data, resp)
                        if attempt < API_REQUEST_MAX_ATTEMPTS and api_error.retryable:
                            LOGGER.debug(
                                "Porkbun API transient status error, retrying (%d/%d): HTTP %s %s",
                                attempt,
                                API_REQUEST_MAX_ATTEMPTS,
                                resp.status,
                                api_error,
                            )
                            await self._sleep_before_retry(attempt, api_error.retry_after)
                            continue
                        raise api_error

                    return data
            except PorkbunAuthError:
                raise
            except (aiohttp.ClientError, TimeoutError) as connection_error:
                if attempt >= API_REQUEST_MAX_ATTEMPTS:
                    raise
                LOGGER.debug(
                    "Porkbun API transient connection error, retrying (%d/%d): %s",
                    attempt,
                    API_REQUEST_MAX_ATTEMPTS,
                    self._error_text(connection_error),
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
            if (
                err.code in self._NO_RECORD_CODES
                or "no records" in str(err).lower()
                or "could not find" in str(err).lower()
            ):
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
        data = await self._request(
            f"dns/create/{domain}",
            extra,
            idempotency_key=secrets.token_hex(16),
        )
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
        await self._request(endpoint, extra, idempotency_key=secrets.token_hex(16))

    async def delete_records_by_name_type(
        self,
        domain: str,
        record_type: str,
        subdomain: str = "",
    ) -> None:
        """Delete DNS records matching domain, type, and optional subdomain."""
        endpoint = f"dns/deleteByNameType/{domain}/{record_type}{f'/{subdomain}' if subdomain else ''}"
        await self._request(endpoint, idempotency_key=secrets.token_hex(16))

    async def get_domain_info(self, domain: str) -> DomainInfo | None:
        """Get domain registration info via domain/listAll."""
        data = await self._request("domain/listAll")
        for d in data.get("domains", []):
            if d.get("domain") == domain:
                return DomainInfo(
                    domain=d["domain"],
                    status=d.get("status", "UNKNOWN"),
                    expire_date=d.get("expireDate", ""),
                    whois_privacy=_api_bool(d.get("whoisPrivacy", False)),
                    auto_renew=_api_bool(d.get("autoRenew", False)),
                )
        return None
