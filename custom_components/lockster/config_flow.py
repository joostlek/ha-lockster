"""Config flow for Lockster."""

from typing import Any

from aiohttp import ClientSession
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_TOKEN, CONF_USER_ID, DOMAIN, LOGGER

NAME_TEMPLATE = "{0} {1}"

schema = vol.Schema({vol.Required(CONF_TOKEN): str})


async def async_get_user(token: str, session: ClientSession) -> dict:
    """Return user info from Lockster."""
    headers = {"Authorization": f"Bearer {token}"}
    response = await session.request(
        "GET",
        "https://api.lockster.bloq.it/api/v1/auth/user",
        headers=headers,
        ssl=True,
    )
    return await response.json()

class LocksterOptionsFlowHandler(OptionsFlow):
    """Handle the options flow for Lockster."""

    async def _show_setup_form(
        self, errors: dict[str, str] | None = None
    ) -> FlowResult:
        """Show the setup form to the user."""
        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors or {},
        )

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage Lockster options."""
        if user_input is None:
            return await self._show_setup_form(user_input)

        session = async_get_clientsession(self.hass)

        try:
            user_info = await async_get_user(user_input[CONF_TOKEN], session)
        except Exception as err:  # pylint: disable=broad-except
            LOGGER.exception(err)
            errors = {"base": "cannot_connect"}
            return await self._show_setup_form(errors)

        return self.async_create_entry(
            title=NAME_TEMPLATE.format(user_info["firstName"], user_info["lastName"]),
            data={
                CONF_TOKEN: user_input[CONF_TOKEN],
                CONF_USER_ID: user_info["id"],
            },
        )


class LocksterConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Lockster."""

    VERSION = 1

    async def _show_setup_form(
        self, errors: dict[str, str] | None = None
    ) -> FlowResult:
        """Show the setup form to the user."""
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors or {},
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initiated by the user."""
        if user_input is None:
            return await self._show_setup_form(user_input)

        session = async_get_clientsession(self.hass)

        try:
            user_info = await async_get_user(user_input[CONF_TOKEN], session)
        except Exception as err:  # pylint: disable=broad-except
            LOGGER.exception(err)
            errors = {"base": "cannot_connect"}
            return await self._show_setup_form(errors)

        return self.async_create_entry(
            title=NAME_TEMPLATE.format(user_info["firstName"], user_info["lastName"]),
            data={
                CONF_TOKEN: user_input[CONF_TOKEN],
                CONF_USER_ID: user_info["id"],
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> LocksterOptionsFlowHandler:
        """Get the options flow for this handler."""
        return LocksterOptionsFlowHandler()
