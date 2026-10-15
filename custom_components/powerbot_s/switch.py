"""Switch platform for POWERbot-S: carpet mode, do not disturb and schedules."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import protocol
from .const import FAN_LEVEL_MAP, WATER_LEVEL_MAP, WORK_MODES
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
    if not coordinator.supported:
        return
    async_add_entities([PowerBotCarpetMode(coordinator), PowerBotDoNotDisturb(coordinator)])

    known: set[int] = set()

    @callback
    def _add_schedules() -> None:
        """Add a switch for each schedule the robot reports, as they appear."""
        new = set(coordinator.schedules) - known
        known.update(new)
        async_add_entities(PowerBotSchedule(coordinator, task_id) for task_id in sorted(new))

    _add_schedules()
    entry.async_on_unload(coordinator.async_add_listener(_add_schedules))


class PowerBotCarpetMode(PowerBotEntity, SwitchEntity):
    """Carpet detection: raise suction on carpets."""

    _attr_translation_key = "carpet_mode"
    _attr_entity_category = EntityCategory.CONFIG

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
    """Do not disturb: the robot stays quiet between the start and end times."""

    _attr_translation_key = "do_not_disturb"
    _attr_entity_category = EntityCategory.CONFIG

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


_DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


class PowerBotSchedule(PowerBotEntity, SwitchEntity):
    """A cleaning schedule made in the POWERbot-S app, turned on or off."""

    _attr_translation_key = "schedule"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: PowerBotDataUpdateCoordinator, task_id: int) -> None:
        super().__init__(coordinator, f"schedule_{task_id}")
        self._task_id = task_id
        self._attr_translation_placeholders = {"task": str(task_id)}

    @property
    def _schedule(self) -> protocol.Schedule | None:
        return self.coordinator.schedules.get(self._task_id)

    @property
    def available(self) -> bool:
        """Unavailable once the schedule is deleted in the app."""
        return super().available and self._schedule is not None

    @property
    def is_on(self) -> bool | None:
        return self._schedule.enabled if self._schedule else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if (schedule := self._schedule) is None:
            return None
        return {
            "days": [_DAYS[day] for day in schedule.days],
            "repeat": schedule.repeat,
            "start": schedule.start.strftime("%H:%M"),
            "duration": schedule.duration,
            "cleaning_mode": WORK_MODES.get(schedule.work_mode, schedule.work_mode),
            "fan_speed": FAN_LEVEL_MAP.get(str(schedule.fan), schedule.fan),
            "water_level": WATER_LEVEL_MAP.get(str(schedule.water), schedule.water),
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_schedule(self._task_id, True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_schedule(self._task_id, False)
        self.async_write_ha_state()
