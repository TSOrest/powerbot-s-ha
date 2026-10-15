"""Switch platform for POWERbot-S: carpet mode and do not disturb."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import protocol
from .coordinator import PowerBotConfigEntry, PowerBotDataUpdateCoordinator
from .entity import PowerBotEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PowerBotConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the switches."""
    coordinator = entry.runtime_data
    async_add_entities([PowerBotCarpetMode(coordinator), PowerBotDoNotDisturb(coordinator)])


class PowerBotCarpetMode(PowerBotEntity, SwitchEntity):
    """Carpet detection: raise suction on carpets.

    The cloud state does not report this setting, so the switch shows the
    last value set from Home Assistant.
    """

    _attr_translation_key = "carpet_mode"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_assumed_state = True

    def __init__(self, coordinator: PowerBotDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "carpet_mode")

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.carpet_mode

    async def _async_set(self, enabled: bool) -> None:
        await self.coordinator.async_send(protocol.carpet_mode(enabled))
        self.coordinator.carpet_mode = enabled
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_set(False)


class PowerBotDoNotDisturb(PowerBotEntity, SwitchEntity):
    """Do not disturb: the robot stays quiet between the start and end times.

    Like carpet mode, the cloud state does not report it, so the switch shows
    the last value set from Home Assistant.
    """

    _attr_translation_key = "do_not_disturb"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_assumed_state = True

    def __init__(self, coordinator: PowerBotDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "do_not_disturb")

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.dnd_enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_dnd(enabled=True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_dnd(enabled=False)
        self.async_write_ha_state()
