"""DataUpdateCoordinator for POWERbot-S."""
from __future__ import annotations

import logging
from datetime import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from . import protocol
from .api import (
    PowerBotApiClient,
    PowerBotApiError,
    PowerBotAuthError,
    PowerBotDeviceTimeoutError,
)
from .const import (
    CONF_DEVICE_ID,
    DEFAULT_FAN,
    DEFAULT_WATER,
    DOMAIN,
    FAN_LEVEL_MAP,
    FAN_LEVELS,
    SCAN_INTERVAL,
    WATER_LEVEL_MAP,
    WATER_LEVELS,
)

_LOGGER = logging.getLogger(__name__)

type PowerBotConfigEntry = ConfigEntry[PowerBotDataUpdateCoordinator]

# How long the cloud waits for the robot to acknowledge a command
COMMAND_WAIT_SECONDS = 15


class PowerBotDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls the robot's state from the cloud and sends it commands."""

    config_entry: PowerBotConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: PowerBotConfigEntry,
        client: PowerBotApiClient,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.client = client
        self.device_id: str = entry.data[CONF_DEVICE_ID]
        # Last values set from Home Assistant, used when the cloud state lacks them
        self.last_water: str = DEFAULT_WATER
        self.carpet_mode: bool | None = None
        self.volume: int | None = None
        self.dnd_enabled: bool | None = None
        self.dnd_start = time(22, 0)
        self.dnd_end = time(8, 0)

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            state = await self.client.async_get_device_state(self.device_id)
        except PowerBotAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except PowerBotApiError as err:
            raise UpdateFailed(f"Error communicating with POWERbot-S cloud: {err}") from err
        if state is None:
            raise UpdateFailed(f"No state returned for device {self.device_id}")
        return state

    @property
    def fan_speed(self) -> str | None:
        level = self.data.get("fanLevel")
        return FAN_LEVEL_MAP.get(str(level)) if level is not None else None

    @property
    def water_level(self) -> str:
        level = self.data.get("waterLevel")
        if level is not None and str(level) in WATER_LEVEL_MAP:
            return WATER_LEVEL_MAP[str(level)]
        return self.last_water

    def levels(self, fan: str | None = None, water: str | None = None) -> tuple[int, int]:
        """Return command bytes for fan and water, filling in current values."""
        fan = fan or self.fan_speed or DEFAULT_FAN
        water = water or self.water_level
        return FAN_LEVELS[fan], WATER_LEVELS[water]

    async def async_set_dnd(
        self,
        enabled: bool | None = None,
        start: time | None = None,
        end: time | None = None,
    ) -> None:
        """Send the do-not-disturb setting, keeping the parts not given."""
        enabled = self.dnd_enabled if enabled is None else enabled
        start = start or self.dnd_start
        end = end or self.dnd_end
        await self.async_send(
            protocol.do_not_disturb(
                bool(enabled), (start.hour, start.minute), (end.hour, end.minute)
            )
        )
        self.dnd_enabled, self.dnd_start, self.dnd_end = bool(enabled), start, end

    async def async_send(self, frame: str) -> None:
        """Send a command frame and refresh the state."""
        try:
            await self.client.async_send_command(
                self.device_id, frame, wait_timeout=COMMAND_WAIT_SECONDS
            )
        except PowerBotDeviceTimeoutError as err:
            raise HomeAssistantError(
                "The robot did not respond. Check that it is online in the POWERbot-S app."
            ) from err
        except PowerBotApiError as err:
            raise HomeAssistantError(f"Command failed: {err}") from err
        await self.async_request_refresh()
