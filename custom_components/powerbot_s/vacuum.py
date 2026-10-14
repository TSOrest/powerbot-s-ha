"""Vacuum platform for POWERbot-S (Samsung VR7700)."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.vacuum import (
    StateVacuumEntity,
    VacuumEntityFeature,
    VacuumActivity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_DEVICE_ID, FAN_LEVEL_MAP, FAN_SPEEDS
from .coordinator import PowerBotDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────────
# Hex commands — reverse-engineered from com.mzbots.android.powerbot v1.2.1 APK.
#
# Protocol format (from OldControl.java / CmdUtil + CRCUtil.java):
#   AA <LEN> B8 00 00 00 00 00 00 <CMD_BYTES> <CRC8>
#
# CRC8 algorithm (CRCUtil.calculateCustomCRC8, two's-complement negation):
#   i = 0
#   for b in data[1:-1]: i = (i + b) % 65535
#   crc = ((~(i & 0xFF)) + 1) & 0xFF
#
# Commands are sent via POST /devices/commands/{deviceId}
# body: {"data": "<hex_string>", "waitTimeoutInSeconds": 30}
# ─────────────────────────────────────────────────────────────────────────────────

# ── Cleaning mode commands ────────────────────────────────────────────
HEX_START_CLEANING   = "AA0DB8000000000000013501010102"   # Auto clean
HEX_STOP_CLEANING    = "AA0DB8000000000000013501010003"   # Stop / pause
HEX_RETURN_TO_BASE   = "AA0DB80000000000000135010104FF"   # Return to dock
HEX_SPOT_CLEAN       = "AA0DB8000000000000013501010201"   # Spot clean
HEX_WALL_FOLLOW      = "AA0DB8000000000000013501010300"   # Wall-follow mode

# ── Fan speed commands ────────────────────────────────────────────
HEX_FAN_QUIET        = "AA0EB800000000000001350201010100FF"  # Quiet / Eco
HEX_FAN_NORMAL       = "AA0EB800000000000001350201010200FE"  # Normal
HEX_FAN_STRONG       = "AA0EB800000000000001350201010300FD"  # Strong / Max

# ── State mapping from API → HA VacuumActivity ───────────────────────────────────────
_STATE_MAP: dict[str, VacuumActivity] = {
    "cleaning":        VacuumActivity.CLEANING,
    "sweeping":        VacuumActivity.CLEANING,
    "mopping":         VacuumActivity.CLEANING,
    "spot":            VacuumActivity.CLEANING,
    "auto_cleaning":   VacuumActivity.CLEANING,
    "wall_follow":     VacuumActivity.CLEANING,
    "paused":          VacuumActivity.PAUSED,
    "pause":           VacuumActivity.PAUSED,
    "charging_finish": VacuumActivity.DOCKED,
    "charging":        VacuumActivity.DOCKED,
    "docked":          VacuumActivity.DOCKED,
    "returning":       VacuumActivity.RETURNING,
    "going_home":      VacuumActivity.RETURNING,
    "idle":            VacuumActivity.IDLE,
    "standby":         VacuumActivity.IDLE,
    "error":           VacuumActivity.ERROR,
    "fault":           VacuumActivity.ERROR,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the vacuum entity."""
    coordinator: PowerBotDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([PowerBotVacuum(coordinator, entry)], True)


class PowerBotVacuum(CoordinatorEntity[PowerBotDataUpdateCoordinator], StateVacuumEntity):
    """Representation of the Samsung VR7700 robot vacuum."""

    _attr_has_entity_name = True
    _attr_name = None  # Use device name as entity name
    _attr_fan_speed_list = FAN_SPEEDS
    _attr_supported_features = (
        VacuumEntityFeature.START
        | VacuumEntityFeature.STOP
        | VacuumEntityFeature.PAUSE
        | VacuumEntityFeature.RETURN_HOME
        | VacuumEntityFeature.BATTERY
        | VacuumEntityFeature.STATE
        | VacuumEntityFeature.FAN_SPEED
        | VacuumEntityFeature.CLEAN_SPOT
        | VacuumEntityFeature.LOCATE
    )

    def __init__(
        self,
        coordinator: PowerBotDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._device_id = entry.data[CONF_DEVICE_ID]
        self._attr_unique_id = f"powerbot_{self._device_id}"

    @property
    def device_info(self) -> dict:
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": "Samsung POWERbot-S",
            "manufacturer": "Samsung / MzBots",
            "model": "VR7700",
        }

    @property
    def activity(self) -> VacuumActivity | None:
        """Return current activity from shadow state."""
        state_str = self.coordinator.data.get("state", "")
        if state_str:
            state_lower = state_str.lower()
            for key, activity in _STATE_MAP.items():
                if key in state_lower:
                    return activity
        return VacuumActivity.IDLE

    @property
    def battery_level(self) -> int | None:
        """Return battery level from shadow state."""
        return self.coordinator.data.get("batteryLevel")

    @property
    def fan_speed(self) -> str | None:
        """Return current fan speed."""
        level = str(self.coordinator.data.get("fanLevel", "2"))
        return FAN_LEVEL_MAP.get(level, "normal")

    async def _send_hex(self, hex_data: str) -> None:
        """Send a hex command to the robot and request a state refresh."""
        await self.coordinator.client.async_send_command(
            self._device_id, hex_data, wait_timeout=30
        )
        await self.coordinator.async_request_refresh()

    # ── Standard vacuum actions ────────────────────────────────────────────

    async def async_start(self) -> None:
        """Start auto cleaning."""
        await self._send_hex(HEX_START_CLEANING)

    async def async_pause(self) -> None:
        """Pause cleaning."""
        await self._send_hex(HEX_STOP_CLEANING)

    async def async_stop(self, **kwargs: Any) -> None:
        """Stop cleaning."""
        await self._send_hex(HEX_STOP_CLEANING)

    async def async_return_to_base(self, **kwargs: Any) -> None:
        """Return to charging dock."""
        await self._send_hex(HEX_RETURN_TO_BASE)

    async def async_clean_spot(self, **kwargs: Any) -> None:
        """Start spot cleaning."""
        await self._send_hex(HEX_SPOT_CLEAN)

    async def async_locate(self, **kwargs: Any) -> None:
        """Locate the robot (no dedicated locate in mzrobo API; triggers spot-clean)."""
        _LOGGER.debug(
            "Locate requested — no dedicated locate command; triggering spot-clean"
        )
        await self._send_hex(HEX_SPOT_CLEAN)

    async def async_set_fan_speed(self, fan_speed: str, **kwargs: Any) -> None:
        """Set fan / suction speed."""
        hex_map = {
            "quiet":  HEX_FAN_QUIET,
            "normal": HEX_FAN_NORMAL,
            "strong": HEX_FAN_STRONG,
        }
        if fan_speed in hex_map:
            await self._send_hex(hex_map[fan_speed])
        else:
            _LOGGER.warning("Unknown fan speed: %s", fan_speed)

    # ── Extra service: wall-follow mode ──────────────────────────────────────

    async def async_wall_follow(self) -> None:
        """Start wall-follow cleaning mode (edge cleaning)."""
        await self._send_hex(HEX_WALL_FOLLOW)
