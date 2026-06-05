"""Services for the ShoppingTajm integration."""

from __future__ import annotations

import logging
from typing import Any, cast

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from .api import ShoppingTajmError
from .const import (
    ATTR_ITEM_ID,
    ATTR_ITEM_IDS,
    ATTR_ITEM_NAME,
    ATTR_LIST_ID,
    ATTR_NAME,
    ATTR_QUANTITY,
    ATTR_STATUS,
    CONF_ENTRY_ID,
    DOMAIN,
    SERVICE_ACTIVATE_LIST,
    SERVICE_ADD_ITEM,
    SERVICE_COMPLETE_ITEM,
    SERVICE_CREATE_LIST,
    SERVICE_DELETE_ITEM,
    SERVICE_REORDER_ITEMS,
    SERVICE_SET_ITEM_QUANTITY,
    SERVICE_UPDATE_ITEM,
)
from .coordinator import ShoppingTajmCoordinator

_LOGGER = logging.getLogger(__name__)

ADD_ITEM_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_LIST_ID): cv.positive_int,
        vol.Required(ATTR_ITEM_NAME): cv.string,
        vol.Optional(CONF_ENTRY_ID): cv.string,
    }
)

ITEM_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ITEM_ID): cv.positive_int,
        vol.Optional(CONF_ENTRY_ID): cv.string,
    }
)

UPDATE_ITEM_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_LIST_ID): cv.positive_int,
        vol.Required(ATTR_ITEM_ID): cv.positive_int,
        vol.Required(ATTR_ITEM_NAME): cv.string,
        vol.Optional(CONF_ENTRY_ID): cv.string,
    }
)

SET_ITEM_QUANTITY_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_LIST_ID): cv.positive_int,
        vol.Required(ATTR_ITEM_ID): cv.positive_int,
        vol.Required(ATTR_QUANTITY): vol.All(
            cv.positive_int, vol.Range(min=1, max=1000)
        ),
        vol.Optional(CONF_ENTRY_ID): cv.string,
    }
)

CREATE_LIST_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_NAME): cv.string,
        vol.Optional(CONF_ENTRY_ID): cv.string,
    }
)

ACTIVATE_LIST_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_LIST_ID): cv.positive_int,
        vol.Optional(CONF_ENTRY_ID): cv.string,
    }
)

REORDER_ITEMS_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_LIST_ID): cv.positive_int,
        vol.Required(ATTR_STATUS): vol.In(["active", "later"]),
        vol.Required(ATTR_ITEM_IDS): [cv.positive_int],
        vol.Optional(CONF_ENTRY_ID): cv.string,
    }
)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register ShoppingTajm services."""
    if hass.services.has_service(DOMAIN, SERVICE_ADD_ITEM):
        return

    async def add_item(call: ServiceCall) -> None:
        coordinator = _coordinator_from_call(hass, call)
        item_name = str(call.data[ATTR_ITEM_NAME]).strip()
        if not item_name:
            raise ServiceValidationError("item_name must not be empty")
        await _call_api(
            coordinator,
            coordinator.api.async_add_item(int(call.data[ATTR_LIST_ID]), item_name),
        )

    async def complete_item(call: ServiceCall) -> None:
        coordinator = _coordinator_from_call(hass, call)
        await _call_api(
            coordinator,
            coordinator.api.async_complete_item(int(call.data[ATTR_ITEM_ID])),
        )

    async def update_item(call: ServiceCall) -> None:
        coordinator = _coordinator_from_call(hass, call)
        item_name = str(call.data[ATTR_ITEM_NAME]).strip()
        if not item_name:
            raise ServiceValidationError("item_name must not be empty")
        await _call_api(
            coordinator,
            coordinator.api.async_update_item_name(
                int(call.data[ATTR_LIST_ID]),
                int(call.data[ATTR_ITEM_ID]),
                item_name,
            ),
        )

    async def set_item_quantity(call: ServiceCall) -> None:
        coordinator = _coordinator_from_call(hass, call)
        await _call_api(
            coordinator,
            coordinator.api.async_set_item_quantity(
                int(call.data[ATTR_LIST_ID]),
                int(call.data[ATTR_ITEM_ID]),
                int(call.data[ATTR_QUANTITY]),
            ),
        )

    async def delete_item(call: ServiceCall) -> None:
        coordinator = _coordinator_from_call(hass, call)
        await _call_api(
            coordinator,
            coordinator.api.async_delete_item(int(call.data[ATTR_ITEM_ID])),
        )

    async def create_list(call: ServiceCall) -> None:
        coordinator = _coordinator_from_call(hass, call)
        name = str(call.data[ATTR_NAME]).strip()
        if not name:
            raise ServiceValidationError("name must not be empty")
        await _call_api(coordinator, coordinator.api.async_create_list(name))

    async def activate_list(call: ServiceCall) -> None:
        coordinator = _coordinator_from_call(hass, call)
        await _call_api(
            coordinator,
            coordinator.api.async_activate_list(int(call.data[ATTR_LIST_ID])),
        )

    async def reorder_items(call: ServiceCall) -> None:
        coordinator = _coordinator_from_call(hass, call)
        item_ids = [int(item_id) for item_id in call.data[ATTR_ITEM_IDS]]
        if not item_ids:
            raise ServiceValidationError("item_ids must not be empty")
        await _call_api(
            coordinator,
            coordinator.api.async_reorder_items(
                int(call.data[ATTR_LIST_ID]),
                str(call.data[ATTR_STATUS]),
                item_ids,
            ),
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_ITEM,
        add_item,
        schema=ADD_ITEM_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_COMPLETE_ITEM,
        complete_item,
        schema=ITEM_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_ITEM,
        update_item,
        schema=UPDATE_ITEM_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_ITEM_QUANTITY,
        set_item_quantity,
        schema=SET_ITEM_QUANTITY_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE_ITEM,
        delete_item,
        schema=ITEM_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_LIST,
        create_list,
        schema=CREATE_LIST_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ACTIVATE_LIST,
        activate_list,
        schema=ACTIVATE_LIST_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REORDER_ITEMS,
        reorder_items,
        schema=REORDER_ITEMS_SCHEMA,
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unregister ShoppingTajm services."""
    for service in (
        SERVICE_ADD_ITEM,
        SERVICE_COMPLETE_ITEM,
        SERVICE_DELETE_ITEM,
        SERVICE_CREATE_LIST,
        SERVICE_ACTIVATE_LIST,
        SERVICE_REORDER_ITEMS,
        SERVICE_UPDATE_ITEM,
        SERVICE_SET_ITEM_QUANTITY,
    ):
        hass.services.async_remove(DOMAIN, service)


async def _call_api(coordinator: ShoppingTajmCoordinator, api_call: Any) -> None:
    """Call an API mutation and refresh coordinator data."""
    try:
        await api_call
    except ShoppingTajmError as err:
        _LOGGER.warning("ShoppingTajm service call failed: %s", err)
        raise HomeAssistantError(str(err)) from err
    await coordinator.async_request_refresh()


def _coordinator_from_call(
    hass: HomeAssistant,
    call: ServiceCall,
) -> ShoppingTajmCoordinator:
    """Return a coordinator for a service call."""
    domain_data: dict[str, Any] = hass.data.get(DOMAIN, {})
    entry_id = call.data.get(CONF_ENTRY_ID)

    if entry_id is not None:
        runtime_data = domain_data.get(entry_id)
        if runtime_data is None:
            raise ServiceValidationError(f"Unknown ShoppingTajm entry_id: {entry_id}")
        return cast(ShoppingTajmCoordinator, runtime_data.coordinator)

    if not domain_data:
        raise ServiceValidationError("No ShoppingTajm config entry is loaded")
    if len(domain_data) > 1:
        raise ServiceValidationError(
            "Multiple ShoppingTajm entries are loaded; provide entry_id"
        )

    runtime_data = next(iter(domain_data.values()))
    return cast(ShoppingTajmCoordinator, runtime_data.coordinator)
