"""The ShoppingTajm Home Assistant integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    ShoppingTajmApiClient,
    ShoppingTajmAuthError,
    ShoppingTajmConnectionError,
    ShoppingTajmError,
)
from .const import (
    CONF_PAT,
    CONF_SERVER_URL,
    CURRENT_ENTRY_VERSION,
    DOMAIN,
    MIN_SUPPORTED_ENTRY_VERSION,
    PLATFORMS,
)
from .coordinator import ShoppingTajmCoordinator
from .services import async_setup_services, async_unload_services
from .websocket import async_register_websocket_commands

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class ShoppingTajmRuntimeData:
    """Runtime data stored on the config entry."""

    api: ShoppingTajmApiClient
    coordinator: ShoppingTajmCoordinator


async def async_setup(hass: HomeAssistant, _config: dict[str, Any]) -> bool:
    """Set up ShoppingTajm services."""
    await async_setup_services(hass)
    async_register_websocket_commands(hass)
    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up ShoppingTajm from a config entry."""
    api = ShoppingTajmApiClient(
        async_get_clientsession(hass),
        entry.data[CONF_SERVER_URL],
        entry.data[CONF_PAT],
    )
    coordinator = ShoppingTajmCoordinator(hass, api)

    try:
        await coordinator.async_config_entry_first_refresh()
    except ShoppingTajmAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except ShoppingTajmConnectionError as err:
        raise ConfigEntryNotReady(str(err)) from err
    except ShoppingTajmError as err:
        raise ConfigEntryNotReady(str(err)) from err

    entry.runtime_data = ShoppingTajmRuntimeData(api=api, coordinator=coordinator)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = entry.runtime_data

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload a ShoppingTajm config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return bool(unload_ok)


async def async_remove_entry(hass: HomeAssistant, _entry: ConfigEntry) -> None:
    """Handle removal of a ShoppingTajm config entry."""
    if not hass.config_entries.async_entries(DOMAIN):
        await async_unload_services(hass)


async def async_migrate_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Migrate old config entries."""
    if entry.version < MIN_SUPPORTED_ENTRY_VERSION:
        _LOGGER.error(
            "ShoppingTajm config entry version %s is no longer supported",
            entry.version,
        )
        return False

    if entry.version == CURRENT_ENTRY_VERSION:
        return True

    _LOGGER.debug(
        "Migrating ShoppingTajm config entry from version %s to %s",
        entry.version,
        CURRENT_ENTRY_VERSION,
    )
    hass.config_entries.async_update_entry(entry, version=CURRENT_ENTRY_VERSION)
    return True
