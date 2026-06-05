"""ShoppingTajm sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import ShoppingTajmData
from .const import DOMAIN
from .coordinator import ShoppingTajmCoordinator
from .entity import ShoppingTajmEntity


@dataclass(frozen=True, kw_only=True)
class ShoppingTajmSensorDescription(SensorEntityDescription):
    """Describe a ShoppingTajm sensor."""

    value_fn: Callable[[ShoppingTajmData], datetime | int | str | None]


SENSORS: tuple[ShoppingTajmSensorDescription, ...] = (
    ShoppingTajmSensorDescription(
        key="total_lists",
        translation_key="total_lists",
        native_unit_of_measurement="lists",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.total_lists,
    ),
    ShoppingTajmSensorDescription(
        key="active_list_name",
        translation_key="active_list_name",
        icon="mdi:format-list-bulleted",
        value_fn=lambda data: data.active_list_name,
    ),
    ShoppingTajmSensorDescription(
        key="remaining_items",
        translation_key="remaining_items",
        native_unit_of_measurement="items",
        icon="mdi:cart-outline",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.remaining_items,
    ),
    ShoppingTajmSensorDescription(
        key="completed_items",
        translation_key="completed_items",
        native_unit_of_measurement="items",
        icon="mdi:cart-check",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.completed_items,
    ),
    ShoppingTajmSensorDescription(
        key="last_updated",
        translation_key="last_updated",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _parse_timestamp(data.last_updated),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ShoppingTajm sensors."""
    coordinator: ShoppingTajmCoordinator = entry.runtime_data.coordinator
    async_add_entities(
        ShoppingTajmSensor(coordinator, entry.entry_id, description)
        for description in SENSORS
    )


class ShoppingTajmSensor(ShoppingTajmEntity, SensorEntity):
    """A ShoppingTajm sensor."""

    entity_description: ShoppingTajmSensorDescription

    def __init__(
        self,
        coordinator: ShoppingTajmCoordinator,
        entry_id: str,
        description: ShoppingTajmSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry_id)
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_{description.key}"

    @property
    def native_value(self) -> datetime | int | str | None:
        """Return the native sensor value."""
        data = self.coordinator.data
        if data is None:
            return None
        return self.entity_description.value_fn(data)

    @property
    def extra_state_attributes(self) -> dict[str, int | str] | None:
        """Return useful attributes for the active list sensor."""
        data = self.coordinator.data
        if data is None or self.entity_description.key != "active_list_name":
            return None
        attributes: dict[str, int | str] = {}
        if data.active_list_id is not None:
            attributes["list_id"] = data.active_list_id
        attributes["server_url"] = data.server_url
        return attributes


def _parse_timestamp(value: str) -> datetime | None:
    """Parse an API timestamp into a Home Assistant timestamp value."""
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
