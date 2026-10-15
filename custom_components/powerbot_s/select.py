"""Select platform for POWERbot-S: suction, mop water level and voice pack."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import protocol
from .const import FAN_SPEEDS, WATER_LEVELS
from .coordinator import PowerBotConfigEntry, PowerBotDataUpdateCoordinator
from .entity import PowerBotEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PowerBotConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the selects."""
    coordinator = entry.runtime_data
    if not coordinator.supported:
        return
    entities: list[SelectEntity] = [PowerBotSuction(coordinator)]
    # Skip the water level on a robot that reports no mop
    if coordinator.has_mop is not False:
        entities.append(PowerBotWaterLevel(coordinator))
    if coordinator.voices:
        entities.append(PowerBotVoice(coordinator))
    async_add_entities(entities)


class PowerBotSuction(PowerBotEntity, SelectEntity):
    """Suction power, the same as the vacuum's fan speed, for dashboards."""

    _attr_translation_key = "suction"
    _attr_options = FAN_SPEEDS

    def __init__(self, coordinator: PowerBotDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "suction")

    @property
    def current_option(self) -> str | None:
        return self.coordinator.fan_speed

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_send(
            protocol.set_suction(*self.coordinator.levels(fan=option))
        )


class PowerBotWaterLevel(PowerBotEntity, SelectEntity):
    """Mop water level; can be changed before or during a clean."""

    _attr_translation_key = "water_level"
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


class PowerBotVoice(PowerBotEntity, SelectEntity):
    """Voice pack. The robot downloads a newly chosen pack by itself."""

    _attr_translation_key = "voice"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: PowerBotDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "voice")
        self._attr_options = list(coordinator.voices.values())

    @property
    def current_option(self) -> str | None:
        voice = self.coordinator.voice
        return self.coordinator.voices.get(voice) if voice is not None else None

    async def async_select_option(self, option: str) -> None:
        index = next(i for i, name in self.coordinator.voices.items() if name == option)
        await self.coordinator.async_send(protocol.select_voice(index))
        self.coordinator.voice = index
        self.async_write_ha_state()
