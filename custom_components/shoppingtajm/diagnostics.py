"""Diagnostics support for ShoppingTajm."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_PAT, DOMAIN

_TO_REDACT = {CONF_PAT}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = getattr(entry, "runtime_data", None)
    coordinator_data = getattr(data, "coordinator", None)
    current = getattr(coordinator_data, "data", None)

    diagnostics: dict[str, Any] = {
        "entry": {
            "entry_id": entry.entry_id,
            "version": entry.version,
            "data": async_redact_data(dict(entry.data), _TO_REDACT),
        },
        "loaded": entry.entry_id in hass.data.get(DOMAIN, {}),
    }

    if current is not None:
        diagnostics["summary"] = {
            "server_url": current.server_url,
            "total_lists": current.total_lists,
            "active_list_id": current.active_list_id,
            "remaining_items": current.remaining_items,
            "completed_items": current.completed_items,
            "last_updated": current.last_updated,
            "list_ids": [item.id for item in current.lists],
            "item_ids": [item.id for item in current.items],
        }

    return diagnostics
