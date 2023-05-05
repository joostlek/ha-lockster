"""Config flow for Lockster."""
# mypy: disable-error-code=empty-body
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


class LocksterFlow:
    """Class to cover all flow related stuff."""

    def __init__(self, step_id: str) -> None:
        """Initialize flow."""
        self._step_id = step_id

    async def _async_show_form(
        self, step_id: str, data_schema: vol.Schema, errors: dict
    ) -> FlowResult:
        pass

    async def _async_create_entry(self, title: str, data: dict[str, Any]) -> FlowResult:
        pass

    async def _show_setup_form(
        self, errors: dict[str, str] | None = None
    ) -> FlowResult:
        """Show the setup form to the user."""
        return await self._async_show_form(
            step_id=self._step_id,
            data_schema=schema,
            errors=errors or {},
        )

    async def _async_handle_form(
        self, session: ClientSession, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Return user info from Lockster."""
        if user_input is None:
            return await self._show_setup_form(user_input)
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

        return await self._async_create_entry(
            title=NAME_TEMPLATE.format(user_info["firstName"], user_info["lastName"]),
            data={
                CONF_TOKEN: user_input[CONF_TOKEN],
                CONF_USER_ID: user_info["id"],
            },
        )


class LocksterOptionsFlowHandler(OptionsFlow, LocksterFlow):
    """Handle the options flow for Lockster."""

    def __init__(self) -> None:
        """Initialize options flow."""
        super().__init__("init")

    async def _async_show_form(
        self, step_id: str, data_schema: vol.Schema, errors: dict
    ) -> FlowResult:
        return self.async_show_form(
            step_id=step_id, data_schema=data_schema, errors=errors
        )

    async def _async_create_entry(self, title: str, data: dict[str, Any]) -> FlowResult:
        return self.async_create_entry(title=title, data={}, options=data)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage Lockster options."""
        return await self._async_handle_form(
            async_get_clientsession(self.hass), user_input
        )


class LocksterConfigFlow(ConfigFlow, LocksterFlow, domain=DOMAIN):
    """Handle a config flow for Lockster."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow."""
        super().__init__("user")

    async def _async_show_form(
        self, step_id: str, data_schema: vol.Schema, errors: dict
    ) -> FlowResult:
        return self.async_show_form(
            step_id=step_id, data_schema=data_schema, errors=errors
        )

    async def _async_create_entry(self, title: str, data: dict[str, Any]) -> FlowResult:
        return self.async_create_entry(title=title, data={}, options=data)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage Lockster options."""
        return await self._async_handle_form(
            async_get_clientsession(self.hass), user_input
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> LocksterOptionsFlowHandler:
        """Get the options flow for this handler."""
        return LocksterOptionsFlowHandler()
