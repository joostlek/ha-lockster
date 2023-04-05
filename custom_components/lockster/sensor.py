"""Sensors for Lockster."""
from __future__ import annotations

from base64 import b64decode
from datetime import datetime, timedelta
from json import loads
from typing import Any

from aiohttp import ClientSession

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.issue_registry import IssueSeverity
from homeassistant.util import Throttle

from .const import (
    CONF_TOKEN,
    CONF_USER_ID,
    DOMAIN,
    ISSUE_TOKEN_EXPIRED,
    ISSUE_TOKEN_EXPIRES,
    LOGGER,
)

UNIQUE_ID_TEMPLATE = "package_{0}_{1}"
ENTITY_ID_TEMPLATE = "sensor.lockster_package_{0}"


def get_friendly_state_name(state):
    """Get friendly name for state."""
    match state:
        case "cancelled" | "finished":
            return state.capitalize()
        case "reserved":
            return "At the hub"
        case "in_progress":
            return "In the Lockster"


class LocksterPackageSensor(SensorEntity):
    """Lockster sensor for individual package."""

    _attr_icon = "mdi:package"

    def __init__(self, data: LocksterData, package: dict) -> None:
        """Initialize sensor."""
        self._data = data
        self._state = get_friendly_state_name(package["state"])
        self._tracking_number = package["externalID"]
        for state in package["states"]:
            if "locker" in state["metadata"]:
                self._locker = state["metadata"]["locker"]
        self._friendly_name = self._tracking_number
        self.entity_id = ENTITY_ID_TEMPLATE.format(self._tracking_number)
        self._attr_unique_id = UNIQUE_ID_TEMPLATE.format(
            package["_id"], self._tracking_number
        )

    @property
    def name(self) -> str:
        """Return tracking number."""
        return self._friendly_name

    @property
    def native_value(self) -> str:
        """Return state of package."""
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the device."""
        try:
            return {"locker": self._locker}
        except AttributeError:
            return {}

    async def async_update(self) -> None:
        """Update the sensor."""
        await self._data.async_update()

        package = self._data.packages.get(self._tracking_number, None)
        self._state = get_friendly_state_name(package["state"])
        for state in package["states"]:
            if "locker" in state["metadata"]:
                self._locker = state["metadata"]["locker"]


class LocksterPickupSensor(SensorEntity):
    """Lockster sensor for amount of packages ready to pickup."""

    def __init__(self, data: LocksterData, count: int) -> None:
        """Initialize sensor."""
        self._data = data
        self._count = count
        self.entity_id = "sensor.lockster_ready_packages"
        self._attr_unique_id = "ready_packages"

    @property
    def icon(self) -> str | None:
        """Return icon."""
        if self._count == 0:
            return "mdi:package-variant-closed-check"
        return "mdi:package-variant"

    @property
    def native_value(self) -> int:
        """Return amount of packages."""
        return self._count

    @property
    def name(self) -> str:
        """Returns name."""
        return "Amount of packages ready to be collected"

    async def async_update(self) -> None:
        """Update the sensor."""
        await self._data.async_update()

        self._count = self._data.count


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Lockster from a config entry."""
    data = LocksterData(entry, async_add_entities, async_get_clientsession(hass), hass)

    await data.async_update()


class LocksterData:
    """Data handler for Lockster."""

    def __init__(
        self,
        config: ConfigEntry,
        async_add_entites,
        session: ClientSession,
        hass: HomeAssistant,
    ) -> None:
        """Initialize data handler."""
        self._async_add_entites = async_add_entites
        self._hass = hass
        self._config = config
        self._session = session
        self.packages: dict[str, Any] = {}
        self.count = 0
        self.first_update = True

        self.async_update = Throttle(timedelta(minutes=10))(self._async_update)

    async def _async_update(self):
        await self._async_update_packages()
        await self._async_update_count()
        await self._async_check_token()

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._config.data[CONF_TOKEN]}"}

    async def _async_update_packages(self):
        try:
            response = await self._session.request(
                "GET",
                f"https://api.lockster.bloq.it/api/v1/rent/list?userID={self._config.data[CONF_USER_ID]}",
                headers=self._headers(),
            )
            response_json = await response.json()
            packages = response_json["rents"]
            new_packages = {p["externalID"]: p for p in packages}
            to_add = set(new_packages) - set(self.packages)
            if to_add:
                LOGGER.debug("Will add new tracking numbers: %s", to_add)
                self._async_add_entites(
                    [
                        LocksterPackageSensor(self, new_packages[tracking_number])
                        for tracking_number in to_add
                    ]
                )
            self.packages = new_packages
        except Exception as err:  # pylint: disable=broad-except
            LOGGER.exception(err)

    async def _async_update_count(self):
        try:
            response = await self._session.request(
                "GET",
                f"https://api.lockster.bloq.it/api/v1/rent/count?userID={self._config.data[CONF_USER_ID]}",
                headers=self._headers(),
            )
            response_json = await response.json()
            amount_to_be_picked_up = response_json["count"]
            self.count = amount_to_be_picked_up

            if self.first_update:
                self.first_update = False

                self._async_add_entites([LocksterPickupSensor(self, self.count)])
        except Exception as err:  # pylint: disable=broad-except
            LOGGER.exception(err)

    async def _async_check_token(self):
        token: str = self._config.data[CONF_TOKEN]
        payload: dict[str, Any] = loads(b64decode(token.split(".")[1] + "==").decode())
        expires_at: datetime = datetime.fromtimestamp(payload["exp"])
        if datetime.now() > expires_at:
            ir.async_create_issue(
                self._hass,
                DOMAIN,
                ISSUE_TOKEN_EXPIRED,
                is_fixable=True,
                is_persistent=True,
                severity=IssueSeverity.CRITICAL,
                issue_domain=DOMAIN,
                translation_key=ISSUE_TOKEN_EXPIRED,
            )
        elif datetime.now() + timedelta(days=7) > expires_at:
            ir.async_create_issue(
                self._hass,
                DOMAIN,
                ISSUE_TOKEN_EXPIRES,
                is_fixable=True,
                is_persistent=True,
                severity=IssueSeverity.WARNING,
                issue_domain=DOMAIN,
                translation_key=ISSUE_TOKEN_EXPIRES,
            )
