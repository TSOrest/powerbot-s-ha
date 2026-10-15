"""Time platform for POWERbot-S: do-not-disturb start and end."""
from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import PowerBotConfigEntry, PowerBotDataUpdateCoordinator
from .entity import PowerBotEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PowerBotConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the do-not-disturb times."""
    coordinator = entry.runtime_data
    async_add_entities(
        [PowerBotDndTime(coordinator, "dnd_start"), PowerBotDndTime(coordinator, "dnd_end")]
    )


class PowerBotDndTime(PowerBotEntity, TimeEntity):
    """Start or end of the do-not-disturb period.

    A change is sent to the robot only while do not disturb is on; otherwise it
    is kept and sent when do not disturb is turned on.
    """

    _attr_entity_category = EntityCategory.CONFIG
    _attr_assumed_state = True

    def __init__(self, coordinator: PowerBotDataUpdateCoordinator, key: str) -> None:
        super().__init__(coordinator, key)
        self._key = key
        self._attr_translation_key = key

    @property
    def native_value(self) -> time:
        return getattr(self.coordinator, self._key)

    async def async_set_value(self, value: time) -> None:
        if self.coordinator.dnd_enabled:
            await self.coordinator.async_set_dnd(**{self._key.removeprefix("dnd_"): value})
        else:
            setattr(self.coordinator, self._key, value)
        self.async_write_ha_state()
