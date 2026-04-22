"""Tests for the Porkbun DDNS repairs platform."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import SOURCE_RECONFIGURE
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.porkbun_ddns.const import DOMAIN
from custom_components.porkbun_ddns.repairs import (
    ApiAccessRepairFlow,
    async_create_fix_flow,
)


async def test_async_create_fix_flow_returns_flow_with_entry_id(
    hass: HomeAssistant,
) -> None:
    flow = await async_create_fix_flow(hass, "api_access_example.com", {"entry_id": "abc123"})
    assert isinstance(flow, ApiAccessRepairFlow)
    assert flow._entry_id == "abc123"


async def test_async_create_fix_flow_handles_missing_data(
    hass: HomeAssistant,
) -> None:
    flow = await async_create_fix_flow(hass, "api_access_example.com", None)
    assert isinstance(flow, ApiAccessRepairFlow)
    assert flow._entry_id == ""


async def test_repair_flow_starts_reconfigure(
    hass: HomeAssistant,
) -> None:
    """Submitting the confirm step kicks off the integration's reconfigure flow."""
    flow = ApiAccessRepairFlow("entry-xyz")
    flow.hass = hass

    init_mock = AsyncMock()
    with patch.object(hass.config_entries.flow, "async_init", init_mock):
        result = await flow.async_step_confirm({})
        # Let the scheduled task run
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    init_mock.assert_awaited_once_with(
        DOMAIN,
        context={"source": SOURCE_RECONFIGURE, "entry_id": "entry-xyz"},
    )


async def test_repair_flow_shows_form_without_input(hass: HomeAssistant) -> None:
    flow = ApiAccessRepairFlow("entry-xyz")
    flow.hass = hass
    result = await flow.async_step_confirm(None)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"
