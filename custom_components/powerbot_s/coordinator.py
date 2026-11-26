"""DataUpdateCoordinator for POWERbot-S."""
from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from datetime import datetime, time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.util import dt as dt_util
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from . import protocol, robot_map
from .api import (
    PowerBotApiClient,
    PowerBotApiError,
    PowerBotAuthError,
    PowerBotDeviceTimeoutError,
    device_id_of,
    model_of,
)
from .const import (
    CONF_DEVICE_ID,
    CONF_PROTO_VERSION,
    CONF_SN8,
    CONSUMABLES,
    SUPPORTED_PROTO_VERSIONS,
    SUPPORTED_SN8,
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
        # Last water level set from Home Assistant, used when neither the cloud
        # state nor the robot reports it
        self.last_water: str | None = None
        # Settings read from the robot itself (None until the first answer)
        self.carpet_mode: bool | None = None
        self.volume: int | None = None
        self.dnd_enabled: bool | None = None
        self.dnd_start: time | None = None
        self.dnd_end: time | None = None
        self.voice: int | None = None
        # Voice packs for this model: voice index -> name
        self.voices: dict[int, str] = {}
        # Consumables: entity key -> remaining life in percent
        self.parts: dict[str, int] = {}
        self._owner_id: str | None = None
        self._polls = 0
        # Model details from the device list, or as saved when it was last read
        # (None if never known)
        self.sn8: str | None = entry.data.get(CONF_SN8)
        self.model: str | None = None
        self.proto_version: int | None = entry.data.get(CONF_PROTO_VERSION)
        self.plugin: str | None = None
        # Read from the robot: False when it reports no mop attached
        self.has_mop: bool | None = None
        self.child_lock: bool | None = None
        # Last work-state reply from the robot
        self.work: protocol.WorkState | None = None
        # Map and rooms from the cloud (None until read)
        self.map_grid: robot_map.Grid | None = None
        self.room_grid: robot_map.Grid | None = None
        self.rooms: dict[int, str] = {}
        self.map_updated: datetime | None = None
        # Cleaning totals (minutes, count, m2) and when the last clean started
        self.totals: dict[str, float] = {}
        self.last_clean: datetime | None = None
        # Robot firmware and Wi-Fi module: part -> installed version, update flag, notes
        self.firmware: dict[str, FirmwareInfo] = {}
        self.auto_update: bool | None = None
        self.wifi: protocol.WifiInfo | None = None
        # Hours since the cliff sensors were last cleaned (the cloud counts minutes)
        self.sensor_hours: float | None = None
        # Cleaning schedules stored on the robot: task id -> schedule
        self.schedules: dict[int, protocol.Schedule] = {}

    @property
    def supported(self) -> bool:
        """True if the robot takes the commands this integration knows.

        Other models, and a robot whose model is not known, are shown read-only
        until their control is confirmed.
        """
        return self.sn8 in SUPPORTED_SN8 and self.proto_version in SUPPORTED_PROTO_VERSIONS

    async def _async_setup(self) -> None:
        """Read what does not change while running: model, owner and voice packs."""
        try:
            devices = await self.client.async_get_devices()
        except PowerBotAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except PowerBotApiError as err:
            if self.sn8 is None:
                # Never guess the model: retry setup until it can be read
                raise UpdateFailed(f"Could not read the robot's model: {err}") from err
            _LOGGER.debug("Could not read the device list, using the saved model: %s", err)
            devices = []
        for device in devices:
            if device_id_of(device) == self.device_id:
                self._read_device(device)
        try:
            if not self.supported:
                return
            await self._async_read_firmware()
            voices = await self.client.async_get_voices(self.sn8)
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
        self.model = product.get("productModel") or device.get("productModel")
        if model := model_of(device):
            self.sn8, self.proto_version = model
            self._save_model()
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

    def _save_model(self) -> None:
        """Keep the model in the config entry for when the device list fails."""
        entry = self.config_entry
        model = {CONF_SN8: self.sn8, CONF_PROTO_VERSION: self.proto_version}
        if any(entry.data.get(key) != value for key, value in model.items()):
            self.hass.config_entries.async_update_entry(entry, data={**entry.data, **model})

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
        await self._async_read_work_state()
        if not slow:
            return
        auto_update = protocol.parse_auto_update(await self._async_query(protocol.query_auto_update()))
        if auto_update is not None:
            self.auto_update = auto_update
        if wifi := protocol.parse_wifi(await self._async_query(protocol.query_wifi())):
            self.wifi = wifi
        await self._async_read_dnd()
        if (voice := protocol.parse_voice(await self._async_query(protocol.query_voice()))) is not None:
            self.voice = voice
        schedules = protocol.parse_schedules(await self._async_query(protocol.query_schedules()))
        if schedules is not None:
            self.schedules = {schedule.task_id: schedule for schedule in schedules}
        if self._owner_id:
            try:
                parts = await self.client.async_get_parts(self.device_id, self._owner_id)
            except PowerBotApiError as err:
                _LOGGER.debug("Could not read consumables: %s", err)
            else:
                self.parts = _remaining(parts)
                self.sensor_hours = _hours(parts.get("sensor_time"))
            await self._async_read_history()
            if self._polls:  # setup already read it
                await self._async_read_firmware()
            await self._async_read_map()

    async def _async_read_work_state(self) -> None:
        if work := protocol.parse_work_state(await self._async_query(protocol.query_work_state())):
            self.volume = work.volume
            self.carpet_mode = work.carpet
            self.has_mop = work.has_mop
            self.work = work
            if work.child_lock is not None:
                self.child_lock = work.child_lock

    async def _async_read_dnd(self) -> None:
        if dnd := protocol.parse_dnd(await self._async_query(protocol.query_dnd())):
            self.dnd_enabled, self.dnd_start, self.dnd_end = dnd.enabled, dnd.start, dnd.end

    async def _async_read_firmware(self) -> None:
        if not self._owner_id:
            return
        try:
            ota = await self.client.async_get_firmware(self.device_id, self._owner_id)
        except PowerBotAuthError:
            raise
        except PowerBotApiError as err:
            _LOGGER.debug("Could not read the firmware version: %s", err)
            return
        for part in ("firmware", "module"):
            if isinstance(info := ota.get(part), dict) and info.get("currVersion"):
                self.firmware[part] = FirmwareInfo(
                    installed=str(info["currVersion"]),
                    update=str(info.get("status")) == "1",
                    latest=str(info.get("newVersion") or "") or None,
                    notes=str(info.get("desc") or "") or None,
                )

    async def _async_read_history(self) -> None:
        """Read cleaning totals and the start of the last clean from the cloud."""
        if not self._owner_id:
            return
        month = dt_util.now().strftime("%Y-%m-01")
        try:
            history = await self.client.async_get_history(self.device_id, self._owner_id, month)
        except PowerBotAuthError:
            raise
        except PowerBotApiError as err:
            _LOGGER.debug("Could not read the cleaning history: %s", err)
            return
        self.totals = _totals(history.get("total"))
        records = history.get("list")
        if records and isinstance(records[0], dict):
            started = dt_util.parse_datetime(str(records[0].get("start_stamp") or ""))
            if started is not None:
                self.last_clean = dt_util.as_utc(
                    started if started.tzinfo else started.replace(tzinfo=dt_util.get_default_time_zone())
                )

    async def _async_read_map(self) -> None:
        """Read the map and rooms the app shows; keep the last good copy."""
        if not self._owner_id:
            return
        try:
            map_text = await self.client.async_get_map(self.device_id, self._owner_id)
            room_text, names = await self.client.async_get_rooms(self.device_id, self._owner_id)
        except PowerBotAuthError:
            raise
        except PowerBotApiError as err:
            _LOGGER.debug("Could not read the map: %s", err)
            return
        # Decompressing a large map takes a while; keep it off the event loop
        map_grid = await self.hass.async_add_executor_job(robot_map.decode_map, map_text)
        room_grid, room_ids = await self.hass.async_add_executor_job(
            robot_map.decode_rooms, room_text
        )
        if (map_grid, room_grid) != (self.map_grid, self.room_grid) and (map_grid or room_grid):
            self.map_grid, self.room_grid = map_grid, room_grid
            self.map_updated = dt_util.utcnow()
        self.rooms = robot_map.room_names(room_ids, names)

    @property
    def fan_speed(self) -> str | None:
        level = self.data.get("fanLevel")
        if level is not None and str(level) in FAN_LEVEL_MAP:
            return FAN_LEVEL_MAP[str(level)]
        return FAN_LEVEL_MAP.get(str(self.work.fan)) if self.work else None

    @property
    def water_level(self) -> str | None:
        level = self.data.get("waterLevel")
        if level is not None and str(level) in WATER_LEVEL_MAP:
            return WATER_LEVEL_MAP[str(level)]
        if self.work and str(self.work.water) in WATER_LEVEL_MAP:
            return WATER_LEVEL_MAP[str(self.work.water)]
        return self.last_water

    async def async_levels(
        self, fan: str | None = None, water: str | None = None
    ) -> tuple[int, int]:
        """Return command bytes for fan and water, filling in the robot's current values.

        The robot takes both at once, so a value it has not reported is read
        first; nothing is sent in its place.
        """
        if not (fan or self.fan_speed) or not (water or self.water_level):
            await self._async_read_work_state()
        fan = fan or self.fan_speed
        water = water or self.water_level
        if fan is None or water is None:
            raise HomeAssistantError(
                "The robot's suction and water level have not been read yet; try again shortly"
            )
        return FAN_LEVELS[fan], WATER_LEVELS[water]

    async def async_set_dnd(
        self,
        enabled: bool | None = None,
        start: time | None = None,
        end: time | None = None,
    ) -> None:
        """Send the do-not-disturb setting, keeping the parts not given.

        Parts not given are read from the robot first; nothing is sent in their place.
        """
        if (enabled is None and self.dnd_enabled is None) or not (start or self.dnd_start) or not (
            end or self.dnd_end
        ):
            await self._async_read_dnd()
        enabled = self.dnd_enabled if enabled is None else enabled
        start = start or self.dnd_start
        end = end or self.dnd_end
        if enabled is None or start is None or end is None:
            raise HomeAssistantError(
                "The do-not-disturb setting has not been read from the robot yet; try again shortly"
            )
        await self.async_send(
            protocol.do_not_disturb(
                bool(enabled), (start.hour, start.minute), (end.hour, end.minute)
            )
        )
        self.dnd_enabled, self.dnd_start, self.dnd_end = bool(enabled), start, end

    async def async_set_schedule(self, task_id: int, enabled: bool) -> None:
        """Turn a schedule stored on the robot on or off."""
        await self.async_send(protocol.schedule_enabled(task_id, enabled))
        if schedule := self.schedules.get(task_id):
            self.schedules[task_id] = replace(schedule, enabled=enabled)

    async def async_rename_room(self, room_id: int, name: str) -> None:
        """Rename a room in the cloud so the app shows the same name."""
        if not self._owner_id:
            raise HomeAssistantError("The robot's owner is unknown; reload the integration")
        try:
            await self.client.async_rename_room(self.device_id, self._owner_id, room_id, name)
        except PowerBotApiError as err:
            raise HomeAssistantError(f"Could not rename the room: {err}") from err
        self.rooms[room_id] = name
        self.async_update_listeners()

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


@dataclass(frozen=True)
class FirmwareInfo:
    """What the cloud says about one firmware part (robot or Wi-Fi module)."""

    installed: str
    update: bool
    latest: str | None = None
    notes: str | None = None


def _hours(minutes: Any) -> float | None:
    try:
        return round(float(minutes) / 60, 1)
    except (TypeError, ValueError):
        return None


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


def _totals(total: Any) -> dict[str, float]:
    """Cleaning totals: worktime in minutes, count and area in m2."""
    if not isinstance(total, dict):
        return {}
    result: dict[str, float] = {}
    for key in ("worktime", "count", "area"):
        try:
            result[key] = float(total[key])
        except (KeyError, TypeError, ValueError):
            continue
    return result
