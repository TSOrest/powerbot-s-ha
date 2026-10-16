"""Binary sensor platform for POWERbot-S."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import STATE_CLEANING, STATE_DOCKED, STATE_ERROR, robot_state
from .coordinator import PowerBotConfigEntry, PowerBotDataUpdateCoordinator
from .entity import PowerBotEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class PowerBotBinarySensorDescription(BinarySensorEntityDescription):
    """Describes a POWERbot-S binary sensor."""

    is_on_fn: Callable[[str, PowerBotDataUpdateCoordinator], bool | None]
    always_available: bool = False


def _is(group: str) -> Callable[[str, PowerBotDataUpdateCoordinator], bool]:
    return lambda state, _: robot_state(state) == group


BINARY_SENSORS: tuple[PowerBotBinarySensorDescription, ...] = (
    PowerBotBinarySensorDescription(
        key="error",
        device_class=BinarySensorDeviceClass.PROBLEM,
        is_on_fn=_is(STATE_ERROR),
    ),
    PowerBotBinarySensorDescription(
        key="cleaning",
        translation_key="cleaning",
        device_class=BinarySensorDeviceClass.RUNNING,
        is_on_fn=_is(STATE_CLEANING),
    ),
    PowerBotBinarySensorDescription(
        key="docked",
        translation_key="docked",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        is_on_fn=_is(STATE_DOCKED),
    ),
    PowerBotBinarySensorDescription(
        key="online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda _, coordinator: coordinator.last_update_success,
        always_available=True,
    ),
    PowerBotBinarySensorDescription(
        key="auto_update",
        translation_key="auto_update",
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda _, coordinator: coordinator.auto_update,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PowerBotConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up binary sensor entities."""
    coordinator = entry.runtime_data
    async_add_entities(
        PowerBotBinarySensor(coordinator, description) for description in BINARY_SENSORS
    )


class PowerBotBinarySensor(PowerBotEntity, BinarySensorEntity):
    """A POWERbot-S binary sensor."""

    entity_description: PowerBotBinarySensorDescription

    def __init__(
        self,
        coordinator: PowerBotDataUpdateCoordinator,
        description: PowerBotBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def available(self) -> bool:
        return self.entity_description.always_available or super().available

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.is_on_fn(self.state_str, self.coordinator)
