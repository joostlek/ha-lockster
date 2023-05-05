"""Lockster repair form."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .config_flow import LocksterFlow


class ExpiredTokenIssue(RepairsFlow, LocksterFlow):
    """Handler for an issue fixing flow."""

    def __init__(self) -> None:
        """Initialize token issue."""
        super().__init__("init")

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Initialize repair form."""
        if user_input and "issue_id" in user_input:
            user_input = None
        return await self._async_handle_form(
            async_get_clientsession(self.hass), user_input
        )

    async def _async_show_form(
        self, step_id: str, data_schema: vol.Schema, errors: dict
    ) -> FlowResult:
        return self.async_show_form(
            step_id=step_id, data_schema=data_schema, errors=errors
        )

    async def _async_create_entry(self, title: str, data: dict[str, Any]) -> FlowResult:
        return self.async_create_entry(title=title, data={}, options=data)


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    """Create flow."""
    return ExpiredTokenIssue()
