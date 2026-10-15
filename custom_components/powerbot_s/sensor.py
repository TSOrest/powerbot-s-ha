"""Sensor platform for POWERbot-S."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONSUMABLES, FAN_SPEEDS
from .coordinator import PowerBotConfigEntry, PowerBotDataUpdateCoordinator
from .entity import PowerBotEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class PowerBotSensorDescription(SensorEntityDescription):
    """Describes a POWERbot-S sensor."""

    value_fn: Callable[[PowerBotDataUpdateCoordinator], Any]


def _connection(coordinator: PowerBotDataUpdateCoordinator) -> str:
    if coordinator.last_update_success and coordinator.data.get("connected", True):
        return "online"
    return "offline"


SENSORS: tuple[PowerBotSensorDescription, ...] = (
    PowerBotSensorDescription(
        key="status",
        translation_key="status",
        value_fn=lambda c: c.data.get("state"),
    ),
    PowerBotSensorDescription(
        key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda c: c.data.get("batteryLevel"),
    ),
    PowerBotSensorDescription(
        key="fan_speed",
        translation_key="fan_speed",
        device_class=SensorDeviceClass.ENUM,
        options=FAN_SPEEDS,
        value_fn=lambda c: c.fan_speed,
    ),
    PowerBotSensorDescription(
        key="connection",
        translation_key="connection",
        device_class=SensorDeviceClass.ENUM,
        options=["online", "offline"],
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_connection,
    ),
    *(
        PowerBotSensorDescription(
            key=f"{key}_life",
            translation_key=f"{key}_life",
            native_unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda c, key=key: c.parts.get(key),
        )
        for key, _ in CONSUMABLES.values()
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PowerBotConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensor entities."""
    coordinator = entry.runtime_data
    async_add_entities(
        PowerBotSensor(coordinator, description)
        for description in SENSORS
        if coordinator.supported or not description.key.endswith("_life")
    )


class PowerBotSensor(PowerBotEntity, SensorEntity):
    """A POWERbot-S sensor."""

    entity_description: PowerBotSensorDescription

    def __init__(
        self,
        coordinator: PowerBotDataUpdateCoordinator,
        description: PowerBotSensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def available(self) -> bool:
        # The connection sensor reports "offline" instead of becoming unavailable.
        return self.entity_description.key == "connection" or super().available

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator)
