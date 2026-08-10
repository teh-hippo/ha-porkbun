"""Tests for the live sandbox support helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, call, patch

from custom_components.porkbun_ddns.api import PorkbunApiError, PorkbunClient

from .sandbox_support import ensure_sandbox_domain


async def test_domain_bootstrap_uses_new_idempotency_key_after_topup() -> None:
    client = AsyncMock(spec=PorkbunClient)
    client._request.side_effect = [
        {"status": "SUCCESS", "domains": []},
        {
            "status": "SUCCESS",
            "response": {
                "avail": "yes",
                "price": "9.73",
            },
        },
        PorkbunApiError("Insufficient funds", code="INSUFFICIENT_FUNDS"),
        {"status": "SUCCESS", "balance": 100000},
        {"status": "SUCCESS", "domain": "ha-porkbun-ci-0123456789.com"},
    ]

    with patch("tests.sandbox_support.secrets.token_hex", return_value="0123456789"):
        domain = await ensure_sandbox_domain(client)

    assert domain == "ha-porkbun-ci-0123456789.com"
    assert client._request.await_args_list == [
        call(
            "domain/listAll",
            {"nameContains": "ha-porkbun-ci-", "apiAccess": "yes"},
        ),
        call("domain/checkDomain/ha-porkbun-ci-0123456789.com"),
        call(
            "domain/create/ha-porkbun-ci-0123456789.com",
            {"cost": 973, "agreeToTerms": "yes"},
            idempotency_key="ha-porkbun-bootstrap-ha-porkbun-ci-0123456789.com",
        ),
        call(
            "sandbox/topup",
            {"amount": 100000},
            idempotency_key="ha-porkbun-topup-ha-porkbun-ci-0123456789.com",
        ),
        call(
            "domain/create/ha-porkbun-ci-0123456789.com",
            {"cost": 973, "agreeToTerms": "yes"},
            idempotency_key="ha-porkbun-bootstrap-ha-porkbun-ci-0123456789.com-after-topup",
        ),
    ]
