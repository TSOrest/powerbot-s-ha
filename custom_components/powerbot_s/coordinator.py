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
    device_id_of,
)
from .const import (
    CONF_DEVICE_ID,
    CONSUMABLES,
    DEFAULT_SN8,
    SUPPORTED_PROTO_VERSIONS,
    SUPPORTED_SN8,
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
# Queries are answered in under a second; don't hold a poll up for long
QUERY_WAIT_SECONDS = 5
# Do-not-disturb, voice and consumables change rarely: read them every Nth poll
SLOW_POLL_EVERY = 10


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
        # Last water level set from Home Assistant, used when the cloud state lacks it
        self.last_water: str = DEFAULT_WATER
        # Settings read from the robot itself (None until the first answer)
        self.carpet_mode: bool | None = None
        self.volume: int | None = None
        self.dnd_enabled: bool | None = None
        self.dnd_start = time(22, 0)
        self.dnd_end = time(8, 0)
        self.voice: int | None = None
        # Voice packs for this model: voice index -> name
        self.voices: dict[int, str] = {}
        # Consumables: entity key -> remaining life in percent
        self.parts: dict[str, int] = {}
        self._owner_id: str | None = None
        self._polls = 0
        # Model details from the device list (None if it could not be read)
        self.sn8: str | None = None
        self.model: str | None = None
        self.proto_version: int | None = None
        self.plugin: str | None = None
        # Read from the robot: False when it reports no mop attached
        self.has_mop: bool | None = None
        # Last work-state reply from the robot
        self.work: protocol.WorkState | None = None

    @property
    def supported(self) -> bool:
        """True if the robot takes the commands this integration knows.

        Other models are shown read-only until their control plugin is analysed.
        If the model could not be read, assume the VR7700 as earlier versions did.
        """
        if self.sn8 is None:
            return True
        return self.sn8 in SUPPORTED_SN8 and self.proto_version in SUPPORTED_PROTO_VERSIONS

    async def _async_setup(self) -> None:
        """Read what does not change while running: model, owner and voice packs."""
        try:
            for device in await self.client.async_get_devices():
                if device_id_of(device) == self.device_id:
                    self._read_device(device)
            if not self.supported:
                return
            voices = await self.client.async_get_voices(self.sn8 or DEFAULT_SN8)
        except PowerBotAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except PowerBotApiError as err:
            _LOGGER.debug("Could not read device details or voice packs: %s", err)
            return
        for voice in voices:
            index = voice.get("voiceIndex", voice.get("id"))
            if str(index).isdigit() and voice.get("title"):
                self.voices[int(index)] = voice["title"]

    def _read_device(self, device: dict[str, Any]) -> None:
        self._owner_id = device.get("ownerId") or device.get("userId")
        product = device.get("product") if isinstance(device.get("product"), dict) else {}
        panel = device.get("panel") or product.get("plugin")
        self.sn8 = product.get("sn8") or device.get("sn8") or DEFAULT_SN8
        self.model = product.get("productModel") or device.get("productModel")
        proto = product.get("protoVersion", device.get("protoVersion", 0))
        self.proto_version = int(proto) if str(proto).isdigit() else None
        if isinstance(panel, dict) and panel.get("name"):
            self.plugin = f"{panel['name']} {panel.get('versionName') or ''}".strip()
        if not self.supported:
            _LOGGER.warning(
                "%s (sn8 %s, protocol %s, plugin %s) is not fully supported yet; "
                "showing its state only",
                self.model or "This robot",
                self.sn8,
                self.proto_version,
                self.plugin,
            )

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            state = await self.client.async_get_device_state(self.device_id)
            if self.supported and state is not None and state.get("connected", True):
                await self._async_read_robot(slow=self._polls % SLOW_POLL_EVERY == 0)
        except PowerBotAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except PowerBotApiError as err:
            raise UpdateFailed(f"Error communicating with POWERbot-S cloud: {err}") from err
        if state is None:
            raise UpdateFailed(f"No state returned for device {self.device_id}")
        self._polls += 1
        return state

    async def _async_query(self, frame: str) -> str | None:
        """Ask the robot something; None if it does not answer."""
        try:
            return await self.client.async_send_command(
                self.device_id, frame, wait_timeout=QUERY_WAIT_SECONDS
            )
        except PowerBotAuthError:
            raise
        except PowerBotApiError as err:
            _LOGGER.debug("Robot did not answer %s: %s", frame, err)
            return None

    async def _async_read_robot(self, slow: bool) -> None:
        """Read settings the cloud state does not carry from the robot."""
        if work := protocol.parse_work_state(await self._async_query(protocol.query_work_state())):
            self.volume = work.volume
            self.carpet_mode = work.carpet
            self.has_mop = work.has_mop
            self.work = work
        if not slow:
            return
        if dnd := protocol.parse_dnd(await self._async_query(protocol.query_dnd())):
            self.dnd_enabled, self.dnd_start, self.dnd_end = dnd.enabled, dnd.start, dnd.end
        if (voice := protocol.parse_voice(await self._async_query(protocol.query_voice()))) is not None:
            self.voice = voice
        if self._owner_id:
            try:
                parts = await self.client.async_get_parts(self.device_id, self._owner_id)
            except PowerBotApiError as err:
                _LOGGER.debug("Could not read consumables: %s", err)
            else:
                self.parts = _remaining(parts)

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


def _remaining(parts: dict[str, Any]) -> dict[str, int]:
    """Turn minutes used into remaining life in percent, as the app does."""
    result: dict[str, int] = {}
    for field, (key, life_hours) in CONSUMABLES.items():
        try:
            used_hours = float(parts[field]) / 60
        except (KeyError, TypeError, ValueError):
            continue
        result[key] = max(0, int(100 * (life_hours - used_hours) / life_hours))
    return result
