"""Config flow for Lockster."""

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_TOKEN, CONF_USER_ID, DOMAIN, LOGGER


class LocksterConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Lockster."""

    VERSION = 1

    async def _show_setup_form(
        self, errors: dict[str, str] | None = None
    ) -> FlowResult:
        """Show the setup form to the user."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_TOKEN): str}),
            errors=errors or {},
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initiated by the user."""
        if user_input is None:
            return await self._show_setup_form(user_input)

        errors = {}

        session = async_get_clientsession(self.hass)

        try:
            headers = {"Authorization": f"Bearer {user_input[CONF_TOKEN]}"}
            response = await session.request(
                "GET",
                "https://api.lockster.bloq.it/api/v1/auth/user",
                headers=headers,
                ssl=True,
            )
            user_info = await response.json()
        except Exception as err:  # pylint: disable=broad-except
            LOGGER.exception(err)
            errors = {"base": "cannot_connect"}
            return await self._show_setup_form(errors)
        name = user_info["firstName"] + " " + user_info["lastName"]
        user_id = user_info["id"]

        return self.async_create_entry(
            title=name,
            data={CONF_TOKEN: user_input[CONF_TOKEN], CONF_USER_ID: user_id},
        )
