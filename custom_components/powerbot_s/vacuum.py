"""Vacuum platform for POWERbot-S (Samsung VR7700)."""
from __future__ import annotations

import asyncio
from typing import Any

from homeassistant.components.vacuum import (
    StateVacuumEntity,
    VacuumActivity,
    VacuumEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import protocol
from .const import (
    FAN_SPEEDS,
    STATE_CLEANING,
    STATE_DOCKED,
    STATE_ERROR,
    STATE_IDLE,
    STATE_PAUSED,
    STATE_RETURNING,
    robot_state,
)
from .coordinator import PowerBotConfigEntry, PowerBotDataUpdateCoordinator
from .entity import PowerBotEntity

PARALLEL_UPDATES = 1

# vacuum.send_command "move": direction -> manual control byte
_DIRECTIONS = {"forward": 1, "back": 2, "left": 3, "right": 4}
_MANUAL_STOP = 0
_MOVE_SECONDS = 1.0
_MOVE_MAX_SECONDS = 5.0
# vacuum.send_command start modes besides the normal whole-house clean
_CLEAN_MODES = {"clean_edge": 3, "clean_spot": 4}

_ACTIVITY: dict[str, VacuumActivity] = {
    STATE_CLEANING: VacuumActivity.CLEANING,
    STATE_PAUSED: VacuumActivity.PAUSED,
    STATE_RETURNING: VacuumActivity.RETURNING,
    STATE_DOCKED: VacuumActivity.DOCKED,
    STATE_IDLE: VacuumActivity.IDLE,
    STATE_ERROR: VacuumActivity.ERROR,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PowerBotConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the vacuum entity."""
    async_add_entities([PowerBotVacuum(entry.runtime_data)])


class PowerBotVacuum(PowerBotEntity, StateVacuumEntity):
    """The Samsung VR7700 robot vacuum."""

    _attr_name = None
    _attr_translation_key = "powerbot"
    _attr_fan_speed_list = FAN_SPEEDS
    _attr_supported_features = (
        VacuumEntityFeature.START
        | VacuumEntityFeature.STOP
        | VacuumEntityFeature.PAUSE
        | VacuumEntityFeature.RETURN_HOME
        | VacuumEntityFeature.STATE
        | VacuumEntityFeature.FAN_SPEED
        | VacuumEntityFeature.LOCATE
        | VacuumEntityFeature.SEND_COMMAND
    )

    def __init__(self, coordinator: PowerBotDataUpdateCoordinator) -> None:
        super().__init__(coordinator, None)
        if not coordinator.supported:
            # Unknown command set: show the state only
            self._attr_supported_features = VacuumEntityFeature.STATE

    @property
    def activity(self) -> VacuumActivity | None:
        state = robot_state(self.coordinator.data.get("state"))
        return _ACTIVITY[state] if state else None

    @property
    def fan_speed(self) -> str | None:
        return self.coordinator.fan_speed

    async def async_start(self) -> None:
        if self.activity == VacuumActivity.PAUSED:
            await self.coordinator.async_send(protocol.resume())
        else:
            await self.coordinator.async_send(protocol.start(*self.coordinator.levels()))

    async def async_pause(self) -> None:
        await self.coordinator.async_send(protocol.pause())

    async def async_stop(self, **kwargs: Any) -> None:
        await self.coordinator.async_send(protocol.stop())

    async def async_return_to_base(self, **kwargs: Any) -> None:
        await self.coordinator.async_send(protocol.dock())

    async def async_locate(self, **kwargs: Any) -> None:
        await self.coordinator.async_send(protocol.locate())

    async def async_set_fan_speed(self, fan_speed: str, **kwargs: Any) -> None:
        if fan_speed not in FAN_SPEEDS:
            raise ServiceValidationError(f"Unknown fan speed: {fan_speed}")
        await self.coordinator.async_send(
            protocol.set_suction(*self.coordinator.levels(fan=fan_speed))
        )

    async def async_send_command(
        self,
        command: str,
        params: dict[str, Any] | list[Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Extra commands: move (a short nudge by hand), clean_edge, clean_spot."""
        params = params if isinstance(params, dict) else {}
        if command in _CLEAN_MODES:
            await self.coordinator.async_send(
                protocol.start(*self.coordinator.levels(), mode=_CLEAN_MODES[command])
            )
            return
        if command != "move":
            raise ServiceValidationError(
                f"Unknown command: {command}. Use move, clean_edge or clean_spot."
            )
        direction = params.get("direction", "forward")
        if direction not in _DIRECTIONS:
            raise ServiceValidationError(
                f"Unknown direction: {direction}. Use {', '.join(_DIRECTIONS)}."
            )
        try:
            seconds = float(params.get("duration", _MOVE_SECONDS))
        except (TypeError, ValueError) as err:
            raise ServiceValidationError("duration must be a number of seconds") from err
        seconds = min(max(seconds, 0.0), _MOVE_MAX_SECONDS)
        await self.coordinator.async_send(protocol.manual(_DIRECTIONS[direction]))
        try:
            await asyncio.sleep(seconds)
        finally:
            # Always stop, so the robot never keeps driving on its own
            await self.coordinator.async_send(protocol.manual(_MANUAL_STOP))
