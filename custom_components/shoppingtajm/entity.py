"""Base entities for ShoppingTajm."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME
from .coordinator import ShoppingTajmCoordinator


class ShoppingTajmEntity(CoordinatorEntity[ShoppingTajmCoordinator]):
    """Base ShoppingTajm entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ShoppingTajmCoordinator,
        entry_id: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._entry_id = entry_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for ShoppingTajm."""
        data = self.coordinator.data
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name=NAME,
            manufacturer="ShoppingTajm",
            model="Shopping List API",
            configuration_url=data.server_url if data else None,
        )
