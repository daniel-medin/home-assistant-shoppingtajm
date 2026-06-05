"""ShoppingTajm data update coordinator."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    ShoppingTajmApiClient,
    ShoppingTajmAuthError,
    ShoppingTajmData,
    ShoppingTajmError,
)
from .const import DEFAULT_SCAN_INTERVAL, NAME

_LOGGER = logging.getLogger(__name__)


class ShoppingTajmCoordinator(DataUpdateCoordinator[ShoppingTajmData]):
    """Coordinate ShoppingTajm data updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: ShoppingTajmApiClient,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=NAME,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.api = api

    async def _async_update_data(self) -> ShoppingTajmData:
        """Fetch data from ShoppingTajm."""
        try:
            return await self.api.async_get_data()
        except ShoppingTajmAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except ShoppingTajmError as err:
            raise UpdateFailed(str(err)) from err
