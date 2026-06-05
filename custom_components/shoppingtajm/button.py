"""ShoppingTajm buttons."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ShoppingTajmCoordinator
from .entity import ShoppingTajmEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ShoppingTajm buttons."""
    coordinator: ShoppingTajmCoordinator = entry.runtime_data.coordinator
    async_add_entities([ShoppingTajmRefreshButton(coordinator, entry.entry_id)])


class ShoppingTajmRefreshButton(ShoppingTajmEntity, ButtonEntity):
    """Button to refresh ShoppingTajm data."""

    _attr_translation_key = "refresh_shopping_data"
    _attr_icon = "mdi:refresh"

    def __init__(self, coordinator: ShoppingTajmCoordinator, entry_id: str) -> None:
        """Initialize the refresh button."""
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_refresh_shopping_data"

    async def async_press(self) -> None:
        """Refresh ShoppingTajm data."""
        await self.coordinator.async_request_refresh()
