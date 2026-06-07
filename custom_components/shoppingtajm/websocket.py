"""WebSocket API for the ShoppingTajm custom card."""

from __future__ import annotations

import base64
from typing import Any, cast

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .api import ShoppingTajmData, ShoppingTajmError
from .const import ATTR_ITEM_ID, ATTR_LIST_ID, CONF_ENTRY_ID, DOMAIN
from .coordinator import ShoppingTajmCoordinator

TYPE_ITEM_AUDIO = "shoppingtajm/item_audio"
TYPE_ITEM_SUGGESTIONS = "shoppingtajm/item_suggestions"


@callback  # type: ignore[untyped-decorator, unused-ignore]
def async_register_websocket_commands(hass: HomeAssistant) -> None:
    """Register ShoppingTajm websocket commands."""
    websocket_api.async_register_command(hass, websocket_item_audio)
    websocket_api.async_register_command(hass, websocket_item_suggestions)


@websocket_api.websocket_command(  # type: ignore[attr-defined, untyped-decorator, unused-ignore]
    {
        vol.Required("type"): TYPE_ITEM_AUDIO,
        vol.Optional(CONF_ENTRY_ID): str,
        vol.Required(ATTR_ITEM_ID): vol.Coerce(int),
        vol.Optional(ATTR_LIST_ID): vol.Coerce(int),
    }
)
@websocket_api.async_response  # type: ignore[attr-defined, untyped-decorator, unused-ignore]
async def websocket_item_audio(
    hass: HomeAssistant,
    connection: Any,
    msg: dict[str, Any],
) -> None:
    """Return ShoppingTajm item audio for the custom card."""
    coordinator = _coordinator_from_msg(hass, msg)
    list_id = msg.get(ATTR_LIST_ID)
    if list_id is None and coordinator.data is not None:
        list_id = coordinator.data.active_list_id

    if list_id is None:
        connection.send_error(msg["id"], "missing_list_id", "Missing list_id")
        return
    if not _is_known_grocery_list_id(coordinator, int(list_id)):
        connection.send_error(
            msg["id"],
            "invalid_list_id",
            "list_id must identify a ShoppingTajm grocery list",
        )
        return

    try:
        audio = await coordinator.api.async_get_item_audio(
            int(list_id),
            int(msg[ATTR_ITEM_ID]),
        )
    except ShoppingTajmError as err:
        connection.send_error(msg["id"], "shoppingtajm_error", str(err))
        return

    connection.send_result(
        msg["id"],
        {
            "content_type": audio.content_type,
            "data": base64.b64encode(audio.content).decode("ascii"),
        },
    )


@websocket_api.websocket_command(  # type: ignore[attr-defined, untyped-decorator, unused-ignore]
    {
        vol.Required("type"): TYPE_ITEM_SUGGESTIONS,
        vol.Optional(CONF_ENTRY_ID): str,
        vol.Optional("query", default=""): str,
        vol.Optional(ATTR_LIST_ID): vol.Coerce(int),
    }
)
@websocket_api.async_response  # type: ignore[attr-defined, untyped-decorator, unused-ignore]
async def websocket_item_suggestions(
    hass: HomeAssistant,
    connection: Any,
    msg: dict[str, Any],
) -> None:
    """Return ShoppingTajm item suggestions for the custom card."""
    coordinator = _coordinator_from_msg(hass, msg)
    list_id = msg.get(ATTR_LIST_ID)
    if list_id is None and coordinator.data is not None:
        list_id = coordinator.data.active_list_id

    if list_id is None:
        connection.send_result(msg["id"], {"suggestions": []})
        return
    if not _is_known_grocery_list_id(coordinator, int(list_id)):
        connection.send_error(
            msg["id"],
            "invalid_list_id",
            "list_id must identify a ShoppingTajm grocery list",
        )
        return

    try:
        suggestions = await coordinator.api.async_get_item_suggestions(
            str(msg.get("query", "")).strip(),
            int(list_id),
        )
    except ShoppingTajmError as err:
        connection.send_error(msg["id"], "shoppingtajm_error", str(err))
        return

    connection.send_result(msg["id"], {"suggestions": suggestions})


def _coordinator_from_msg(
    hass: HomeAssistant,
    msg: dict[str, Any],
) -> ShoppingTajmCoordinator:
    """Return a coordinator for a websocket command."""
    domain_data: dict[str, Any] = hass.data.get(DOMAIN, {})
    entry_id = msg.get(CONF_ENTRY_ID)

    if entry_id is not None:
        runtime_data = domain_data[entry_id]
        return cast(ShoppingTajmCoordinator, runtime_data.coordinator)

    runtime_data = next(iter(domain_data.values()))
    return cast(ShoppingTajmCoordinator, runtime_data.coordinator)


def _is_known_grocery_list_id(
    coordinator: ShoppingTajmCoordinator,
    list_id: int,
) -> bool:
    """Return whether a list ID belongs to the filtered grocery list set."""
    data = cast(ShoppingTajmData | None, getattr(coordinator, "data", None))
    if data is None:
        return True
    return any(item.id == list_id for item in data.lists)
