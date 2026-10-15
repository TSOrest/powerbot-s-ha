"""Select platform for POWERbot-S: mop water level."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import protocol
from .const import WATER_LEVELS
from .coordinator import PowerBotConfigEntry, PowerBotDataUpdateCoordinator
from .entity import PowerBotEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PowerBotConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the water level select."""
    async_add_entities([PowerBotWaterLevel(entry.runtime_data)])


class PowerBotWaterLevel(PowerBotEntity, SelectEntity):
    """Mop water level."""

    _attr_translation_key = "water_level"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = list(WATER_LEVELS)

    def __init__(self, coordinator: PowerBotDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "water_level")

    @property
    def current_option(self) -> str | None:
        return self.coordinator.water_level

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_send(
            protocol.set_suction(*self.coordinator.levels(water=option))
        )
        self.coordinator.last_water = option
        self.async_write_ha_state()
