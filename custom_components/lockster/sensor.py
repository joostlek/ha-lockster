"""Sensors for Lockster."""
from __future__ import annotations

from datetime import timedelta

from aiohttp import ClientSession

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import Throttle

from .const import CONF_TOKEN, CONF_USER_ID, LOGGER

UNIQUE_ID_TEMPLATE = "package_{0}_{1}"
ENTITY_ID_TEMPLATE = "sensor.lockster_package_{0}"


class LocksterPackageSensor(SensorEntity):
    """Lockster sensor for individual package."""

    _attr_icon = "mdi:package"

    def __init__(self, data, package) -> None:
        """Initialize sensor."""
        self._data = data
        self._state = package["state"]
        self._tracking_number = package["externalID"]
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

    async def async_update(self) -> None:
        """Update the sensor."""
        await self._data.async_update()


class LocksterPickupSensor(SensorEntity):
    """Lockster sensor for amount of packages ready to pickup."""

    def __init__(self, data, count) -> None:
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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Twente Milieu from a config entry."""
    data = LocksterData(entry, async_add_entities, async_get_clientsession(hass))

    await data.async_update()


class LocksterData:
    """Data handler for Lockster."""

    def __init__(
        self, config: ConfigEntry, async_add_entites, session: ClientSession
    ) -> None:
        """Initialize data handler."""
        self._async_add_entites = async_add_entites
        self._config = config
        self._session = session

        self.async_update = Throttle(timedelta(minutes=10))(self._async_update)

    async def _async_update(self):
        try:
            headers = {"Authorization": f"Bearer {self._config.data[CONF_TOKEN]}"}
            response = await self._session.request(
                "GET",
                f"https://api.lockster.bloq.it/api/v1/rent/list?userID={self._config.data[CONF_USER_ID]}",
                headers=headers,
            )
            response_json = await response.json()
            packages = response_json["rents"]
            new_packages = {p["externalID"]: p for p in packages}
            self._async_add_entites(
                [
                    LocksterPackageSensor(self, new_packages[tracking_number])
                    for tracking_number in new_packages
                ]
            )
            response = await self._session.request(
                "GET",
                f"https://api.lockster.bloq.it/api/v1/rent/count?userID={self._config.data[CONF_USER_ID]}",
                headers=headers,
            )
            response_json = await response.json()
            amount_to_be_picked_up = response_json["count"]
            self._async_add_entites(
                [LocksterPickupSensor(self, amount_to_be_picked_up)]
            )
        except Exception as err:  # pylint: disable=broad-except
            LOGGER.exception(err)
