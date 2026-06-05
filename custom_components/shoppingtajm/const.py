"""Constants for the ShoppingTajm integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "shoppingtajm"
NAME: Final = "Shoppingtajm"
DEFAULT_SERVER_URL: Final = "https://shoppingtajm.se"
DEFAULT_SCAN_INTERVAL: Final = timedelta(seconds=60)

CONF_SERVER_URL: Final = "server_url"
CONF_PAT: Final = "personal_access_token"
CONF_ENTRY_ID: Final = "entry_id"

PLATFORMS: Final = [Platform.SENSOR, Platform.BUTTON]

ATTR_LIST_ID: Final = "list_id"
ATTR_ITEM_ID: Final = "item_id"
ATTR_ITEM_IDS: Final = "item_ids"
ATTR_ITEM_NAME: Final = "item_name"
ATTR_NAME: Final = "name"
ATTR_QUANTITY: Final = "quantity"
ATTR_STATUS: Final = "status"

SERVICE_ADD_ITEM: Final = "add_item"
SERVICE_COMPLETE_ITEM: Final = "complete_item"
SERVICE_DELETE_ITEM: Final = "delete_item"
SERVICE_CREATE_LIST: Final = "create_list"
SERVICE_ACTIVATE_LIST: Final = "activate_list"
SERVICE_REORDER_ITEMS: Final = "reorder_items"
SERVICE_UPDATE_ITEM: Final = "update_item"
SERVICE_SET_ITEM_QUANTITY: Final = "set_item_quantity"

STATUS_ACTIVE: Final = "active"
STATUS_COMPLETED: Final = "cart"
STATUS_LATER: Final = "later"

MIN_SUPPORTED_ENTRY_VERSION: Final = 1
CURRENT_ENTRY_VERSION: Final = 1
