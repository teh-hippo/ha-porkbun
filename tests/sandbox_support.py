"""Helpers for safely exercising Porkbun's isolated sandbox API."""

from __future__ import annotations

import os
import secrets
from decimal import Decimal

import aiohttp

from custom_components.porkbun_ddns.api import PorkbunApiError, PorkbunClient

DOMAIN_PREFIX = "ha-porkbun-ci-"
SANDBOX_API_KEY_ENV = "PORKBUN_SANDBOX_API_KEY"
SANDBOX_SECRET_KEY_ENV = "PORKBUN_SANDBOX_SECRET_KEY"


def sandbox_credentials() -> tuple[str, str]:
    """Return validated sandbox credentials from the environment."""
    api_key = os.environ.get(SANDBOX_API_KEY_ENV, "")
    secret_key = os.environ.get(SANDBOX_SECRET_KEY_ENV, "")
    if not api_key or not secret_key:
        raise RuntimeError(f"{SANDBOX_API_KEY_ENV} and {SANDBOX_SECRET_KEY_ENV} are required")
    if not api_key.startswith("pk1_sb_") or not secret_key.startswith("sk1_sb_"):
        raise RuntimeError("Refusing to run live tests with non-sandbox Porkbun credentials")
    return api_key, secret_key


def sandbox_client(session: aiohttp.ClientSession) -> PorkbunClient:
    """Create a Porkbun client using validated sandbox credentials."""
    api_key, secret_key = sandbox_credentials()
    return PorkbunClient(session, api_key, secret_key)


def _registration_cost(response: dict[str, object]) -> int:
    """Convert a domain availability quote from dollars to integer cents."""
    quote = response.get("response")
    if not isinstance(quote, dict):
        raise RuntimeError("Porkbun sandbox returned no domain quote")
    price = quote.get("price")
    if price is None:
        raise RuntimeError("Porkbun sandbox domain quote had no price")
    return int(Decimal(str(price)) * 100)


async def _matching_domains(client: PorkbunClient) -> list[str]:
    """List reusable project domains already registered in the sandbox."""
    data = await client._request(
        "domain/listAll",
        {"nameContains": DOMAIN_PREFIX, "apiAccess": "yes"},
    )
    domains = data.get("domains", [])
    if not isinstance(domains, list):
        raise RuntimeError("Porkbun sandbox returned an invalid domain list")
    return sorted(
        str(domain["domain"])
        for domain in domains
        if isinstance(domain, dict)
        and isinstance(domain.get("domain"), str)
        and str(domain["domain"]).startswith(DOMAIN_PREFIX)
    )


async def ensure_sandbox_domain(client: PorkbunClient) -> str:
    """Reuse or provision a persistent project domain in the sandbox."""
    if domains := await _matching_domains(client):
        return domains[0]

    for _ in range(5):
        candidate = f"{DOMAIN_PREFIX}{secrets.token_hex(5)}.com"
        quote = await client._request(f"domain/checkDomain/{candidate}")
        quote_response = quote.get("response")
        if not isinstance(quote_response, dict) or quote_response.get("avail") != "yes":
            continue

        payload = {
            "cost": _registration_cost(quote),
            "agreeToTerms": "yes",
        }
        try:
            await client._request(
                f"domain/create/{candidate}",
                payload,
                idempotency_key=f"ha-porkbun-bootstrap-{candidate}",
            )
        except PorkbunApiError as err:
            if err.code == "INSUFFICIENT_FUNDS":
                await client._request(
                    "sandbox/topup",
                    {"amount": 100000},
                    idempotency_key=f"ha-porkbun-topup-{candidate}",
                )
                await client._request(
                    f"domain/create/{candidate}",
                    payload,
                    idempotency_key=f"ha-porkbun-bootstrap-{candidate}-after-topup",
                )
            elif err.code == "DOMAIN_NOT_AVAILABLE":
                continue
            else:
                raise
        return candidate

    if domains := await _matching_domains(client):
        return domains[0]
    raise RuntimeError("Unable to provision a reusable Porkbun sandbox domain")
