"""Vacuum platform for POWERbot-S (Samsung VR7700)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.vacuum import (
    StateVacuumEntity,
    VacuumActivity,
    VacuumEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import PowerBotApiError, PowerBotDeviceTimeoutError
from .const import (
    CLEANING_STATES,
    DOCKED_STATES,
    ERROR_STATES,
    FAN_LEVEL_MAP,
    FAN_SPEEDS,
    IDLE_STATES,
    PAUSED_STATES,
    RETURNING_STATES,
)
from .coordinator import PowerBotConfigEntry
from .entity import PowerBotEntity

PARALLEL_UPDATES = 1

# ─────────────────────────────────────────────────────────────────────────────
# Hex commands, reverse-engineered from com.mzbots.android.powerbot v1.2.1.
#
# Frame: AA <LEN> B8 00 00 00 00 00 00 <CMD_BYTES> <CRC8>
# CRC8 (CRCUtil.calculateCustomCRC8): two's-complement of the byte sum of
# everything between the AA header and the CRC byte.
# ─────────────────────────────────────────────────────────────────────────────
HEX_START_CLEANING = "AA0DB8000000000000013501010102"  # Auto clean
HEX_STOP_CLEANING  = "AA0DB8000000000000013501010003"  # Stop / pause
HEX_RETURN_TO_BASE = "AA0DB80000000000000135010104FF"  # Return to dock
HEX_SPOT_CLEAN     = "AA0DB8000000000000013501010201"  # Spot clean

HEX_FAN_SPEED = {
    "quiet":  "AA0EB800000000000001350201010100FF",
    "normal": "AA0EB800000000000001350201010200FE",
    "strong": "AA0EB800000000000001350201010300FD",
}

# Checked in order: the first group whose substring appears in the state wins.
_ACTIVITY_MAP: tuple[tuple[tuple[str, ...], VacuumActivity], ...] = (
    (ERROR_STATES, VacuumActivity.ERROR),
    (RETURNING_STATES, VacuumActivity.RETURNING),
    (PAUSED_STATES, VacuumActivity.PAUSED),
    (CLEANING_STATES, VacuumActivity.CLEANING),
    (DOCKED_STATES, VacuumActivity.DOCKED),
    (IDLE_STATES, VacuumActivity.IDLE),
)


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
        | VacuumEntityFeature.CLEAN_SPOT
    )

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, None)

    @property
    def activity(self) -> VacuumActivity | None:
        state = self.state_str
        if not state:
            return None
        for keys, activity in _ACTIVITY_MAP:
            if any(key in state for key in keys):
                return activity
        return VacuumActivity.IDLE

    @property
    def fan_speed(self) -> str | None:
        level = self.coordinator.data.get("fanLevel")
        return FAN_LEVEL_MAP.get(str(level)) if level is not None else None

    async def _send_hex(self, hex_data: str) -> None:
        try:
            await self.coordinator.client.async_send_command(
                self.coordinator.device_id, hex_data, wait_timeout=30
            )
        except PowerBotDeviceTimeoutError as err:
            raise HomeAssistantError(
                "The robot did not respond. Check that it is online in the POWERbot-S app."
            ) from err
        except PowerBotApiError as err:
            raise HomeAssistantError(f"Command failed: {err}") from err
        await self.coordinator.async_request_refresh()

    async def async_start(self) -> None:
        await self._send_hex(HEX_START_CLEANING)

    async def async_pause(self) -> None:
        await self._send_hex(HEX_STOP_CLEANING)

    async def async_stop(self, **kwargs: Any) -> None:
        await self._send_hex(HEX_STOP_CLEANING)

    async def async_return_to_base(self, **kwargs: Any) -> None:
        await self._send_hex(HEX_RETURN_TO_BASE)

    async def async_clean_spot(self, **kwargs: Any) -> None:
        await self._send_hex(HEX_SPOT_CLEAN)

    async def async_set_fan_speed(self, fan_speed: str, **kwargs: Any) -> None:
        if fan_speed not in HEX_FAN_SPEED:
            raise HomeAssistantError(f"Unknown fan speed: {fan_speed}")
        await self._send_hex(HEX_FAN_SPEED[fan_speed])
