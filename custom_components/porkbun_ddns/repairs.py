"""Repairs platform for Porkbun DDNS."""

from __future__ import annotations

from typing import Any

from homeassistant.components.repairs import ConfirmRepairFlow, RepairsFlow
from homeassistant.config_entries import SOURCE_RECONFIGURE
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN


class ApiAccessRepairFlow(ConfirmRepairFlow):
    """Repair flow that launches the integration's reconfigure flow."""

    def __init__(self, entry_id: str) -> None:
        """Store the affected config entry id."""
        super().__init__()
        self._entry_id = entry_id

    async def async_step_confirm(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Confirm and start the reconfigure flow for the affected entry."""
        if user_input is not None:
            self.hass.async_create_task(
                self.hass.config_entries.flow.async_init(
                    DOMAIN,
                    context={"source": SOURCE_RECONFIGURE, "entry_id": self._entry_id},
                )
            )
            return self.async_create_entry(data={})

        return self.async_show_form(step_id="confirm", data_schema=None)


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    """Create a fix flow for a Porkbun DDNS repair issue."""
    del hass, issue_id  # unused; entry_id is in data
    entry_id = ""
    if data:
        entry_id = str(data.get("entry_id") or "")
    return ApiAccessRepairFlow(entry_id)
