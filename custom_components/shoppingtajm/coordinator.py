"""ShoppingTajm data update coordinator."""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from typing import Final

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    ShoppingTajmApiClient,
    ShoppingTajmAuthError,
    ShoppingTajmData,
    ShoppingTajmError,
    ShoppingTajmNotFoundError,
)
from .const import DEFAULT_SCAN_INTERVAL, NAME

_LOGGER = logging.getLogger(__name__)
_SSE_CHANGED_EVENT: Final = "shoppingtajm_changed"
_SSE_RECONNECT_DELAY: Final = 1.0
_SSE_MAX_RECONNECT_DELAY: Final = 60.0


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
        self._sse_listener_task: asyncio.Task[None] | None = None
        self._last_sse_event_id: str | None = None

    def async_start_sse_listener(self) -> None:
        """Start listening for ShoppingTajm push updates."""
        if self._sse_listener_task is not None and not self._sse_listener_task.done():
            return
        self._sse_listener_task = self.hass.async_create_task(
            self._async_sse_listener(),
            name="shoppingtajm_sse_listener",
        )

    async def async_stop_sse_listener(self) -> None:
        """Stop listening for ShoppingTajm push updates."""
        if self._sse_listener_task is None:
            return

        self._sse_listener_task.cancel()
        with suppress(asyncio.CancelledError):
            await self._sse_listener_task
        self._sse_listener_task = None

    async def _async_update_data(self) -> ShoppingTajmData:
        """Fetch data from ShoppingTajm."""
        try:
            return await self.api.async_get_data()
        except ShoppingTajmAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except ShoppingTajmError as err:
            raise UpdateFailed(str(err)) from err

    async def _async_sse_listener(self) -> None:
        """Listen for ShoppingTajm events and push fresh data to entities."""
        delay = _SSE_RECONNECT_DELAY

        while True:
            try:
                async for event in self.api.async_iter_events(self._last_sse_event_id):
                    delay = _SSE_RECONNECT_DELAY
                    if event.id is not None:
                        self._last_sse_event_id = event.id
                    if event.event != _SSE_CHANGED_EVENT:
                        continue
                    await self._async_refresh_from_push()
            except asyncio.CancelledError:
                raise
            except ShoppingTajmNotFoundError:
                _LOGGER.debug(
                    "ShoppingTajm SSE endpoint is unavailable; using polling fallback"
                )
                return
            except ShoppingTajmAuthError as err:
                _LOGGER.warning(
                    "ShoppingTajm SSE authentication failed; using polling "
                    "fallback: %s",
                    err,
                )
                return
            except ShoppingTajmError as err:
                _LOGGER.warning(
                    "ShoppingTajm SSE listener disconnected: %s; reconnecting in %.0f "
                    "seconds",
                    err,
                    delay,
                )

            await asyncio.sleep(delay)
            delay = min(delay * 2, _SSE_MAX_RECONNECT_DELAY)

    async def _async_refresh_from_push(self) -> None:
        """Fetch fresh status after a ShoppingTajm change event."""
        try:
            data = await self.api.async_get_data()
        except ShoppingTajmError as err:
            _LOGGER.warning("ShoppingTajm push refresh failed: %s", err)
            return
        self.async_set_updated_data(data)
