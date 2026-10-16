"""Command frames for the POWERbot-S (VR7700).

Taken from the app's control plugin (T0xB8_610VR510 v2.2.46):
  AA <0x0A + len(body)> B8 00 00 00 00 00 00 <msg type> <body> <checksum>
Control commands use msg type 0x02 and a body starting with 0x22 and a
sub-command byte. The checksum is the two's complement of the byte sum
between the AA header and the checksum.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import time

_DEVICE_TYPE = 0xB8
_MSG_CONTROL = 0x02
_MSG_QUERY = 0x03
_CONTROL = 0x22

_START = 0x02
_DOCK = 0x01
_STOP = 0x03
_PAUSE = 0x1B
_CONTINUE = 0x1C
_SET_SUCTION = 0x04
_CARPET = 0x0C
_DND = 0x06
_VOLUME = 0x0A
_VOICE = 0x0B
_CHILD_LOCK = 0x32

_LOCATE = bytes([0x35, 0x07, 0, 0, 0, 0, 0])
_QUERY_WORK_STATE = bytes([0x32, 0x01])
_QUERY_DND = bytes([0x32, 0x05])
_QUERY_VOICE = bytes([0x36])
_QUERY_SCHEDULES = bytes([0x34, 0x01])
_QUERY_AUTO_UPDATE = bytes([0x35, 0x15, 0, 0, 0, 0, 0])
_QUERY_WIFI = bytes([0x35, 0x16, 0, 0, 0, 0, 0])

_SCHEDULE = 0x24
_SCHEDULE_ON = 0x06
_SCHEDULE_OFF = 0x05
_SCHEDULE_ENTRY = 30

_WORK_MODE_AUTO = 0x08


def build_frame(body: bytes, msg_type: int = _MSG_CONTROL) -> str:
    """Wrap a body into a full frame and return it as upper-case hex."""
    frame = bytearray([0xAA, 0x0A + len(body), _DEVICE_TYPE, 0, 0, 0, 0, 0, 0, msg_type])
    frame += body
    frame.append(-sum(frame[1:]) & 0xFF)
    return frame.hex().upper()


def start(fan: int, water: int, mode: int = _WORK_MODE_AUTO) -> str:
    """Start a clean in the given work mode (whole house by default)."""
    return build_frame(bytes([_CONTROL, _START, 0, 2, 0, mode, fan, 0, water, 0, 0]))


_WORK_MODE_ROOMS = 0x0A
MAX_ROOMS = 10


def clean_rooms(fan: int, water: int, rooms: list[tuple[int, int]]) -> str:
    """Clean the given rooms, as (room id, times) pairs; up to 10 rooms."""
    slots = bytearray(2 * MAX_ROOMS)
    for i, (room_id, times) in enumerate(rooms[:MAX_ROOMS]):
        slots[2 * i : 2 * i + 2] = bytes([room_id, times])
    return build_frame(bytes([_CONTROL, _START, 0, 2, 0, _WORK_MODE_ROOMS, fan, 0, water, 0]) + slots)


def manual(direction: int) -> str:
    """Drive by hand: 0 stop, 1 forward, 2 back, 3 left, 4 right."""
    return build_frame(bytes([_CONTROL, _START, 0, 1, direction, 0, 0, 0, 0, 0, 0]))


def schedule_enabled(task_id: int, enabled: bool) -> str:
    """Turn an existing schedule on or off."""
    action = _SCHEDULE_ON if enabled else _SCHEDULE_OFF
    return build_frame(bytes([_SCHEDULE, 0, action, *([0] * 11), task_id]))


def dock() -> str:
    return build_frame(bytes([_CONTROL, _DOCK, 0]))


def stop() -> str:
    return build_frame(bytes([_CONTROL, _STOP, 0]))


def pause() -> str:
    return build_frame(bytes([_CONTROL, _PAUSE, 0]))


def resume() -> str:
    return build_frame(bytes([_CONTROL, _CONTINUE, 0]))


def set_suction(fan: int, water: int) -> str:
    """Set suction and mop water level together (the robot takes both at once)."""
    return build_frame(bytes([_CONTROL, _SET_SUCTION, fan, 0, water, 1]))


def carpet_mode(enabled: bool) -> str:
    return build_frame(bytes([_CONTROL, _CARPET, int(enabled)]))


def locate() -> str:
    """Make the robot play a sound so it can be found."""
    return build_frame(_LOCATE, msg_type=_MSG_QUERY)


def volume(level: int) -> str:
    """Set the voice volume, 0-100."""
    return build_frame(bytes([_CONTROL, _VOLUME, level]))


def do_not_disturb(enabled: bool, start: tuple[int, int], end: tuple[int, int]) -> str:
    """Turn do-not-disturb on or off for the period start-end, as (hour, minute)."""
    return build_frame(bytes([_CONTROL, _DND, int(enabled), *start, *end]))


def child_lock(enabled: bool) -> str:
    """Lock or unlock the robot's buttons."""
    return build_frame(bytes([_CONTROL, _CHILD_LOCK, int(enabled)]))


def select_voice(index: int) -> str:
    """Switch to a voice pack; the robot downloads it itself."""
    return build_frame(bytes([_CONTROL, _VOICE, index]))


# Queries. The cloud returns the robot's reply frame as hex.

def query_work_state() -> str:
    return build_frame(_QUERY_WORK_STATE, msg_type=_MSG_QUERY)


def query_dnd() -> str:
    return build_frame(_QUERY_DND, msg_type=_MSG_QUERY)


def query_voice() -> str:
    return build_frame(_QUERY_VOICE, msg_type=_MSG_QUERY)


def query_schedules() -> str:
    return build_frame(_QUERY_SCHEDULES, msg_type=_MSG_QUERY)


def query_auto_update() -> str:
    return build_frame(_QUERY_AUTO_UPDATE, msg_type=_MSG_QUERY)


def query_wifi() -> str:
    return build_frame(_QUERY_WIFI, msg_type=_MSG_QUERY)


@dataclass(frozen=True)
class WorkState:
    """Settings read from the work-state reply (type 0x03, body 32 01)."""

    fan: int
    water: int
    volume: int
    carpet: bool
    has_mop: bool
    work_mode: int = 0
    area: int = 0  # m2 cleaned in the current or last job
    work_time: int = 0  # minutes
    fault_class: int = 0
    fault_code: int = 0
    child_lock: bool | None = None  # only in replies longer than 47 bytes


@dataclass(frozen=True)
class Schedule:
    """A cleaning schedule stored on the robot."""

    task_id: int
    days: tuple[int, ...]  # 0 = Monday ... 6 = Sunday
    repeat: bool
    start: time
    duration: int  # minutes
    work_mode: int
    fan: int
    water: int
    enabled: bool


@dataclass(frozen=True)
class WifiInfo:
    """The robot's Wi-Fi connection (reply to 35 16)."""

    ip: str
    ssid: str
    rssi: int  # dBm


@dataclass(frozen=True)
class DoNotDisturb:
    enabled: bool
    start: time
    end: time


def _reply(hex_frame: str | None, body: bytes, min_len: int) -> bytes | None:
    """Return the reply as bytes if it is a query reply with this body prefix."""
    if not isinstance(hex_frame, str):
        return None
    try:
        frame = bytes.fromhex(hex_frame)
    except ValueError:
        return None
    if (
        len(frame) < min_len
        or frame[0] != 0xAA
        or frame[9] != _MSG_QUERY
        or frame[10 : 10 + len(body)] != body
    ):
        return None
    return frame


def parse_work_state(hex_frame: str | None) -> WorkState | None:
    if (frame := _reply(hex_frame, _QUERY_WORK_STATE, 29)) is None:
        return None
    return WorkState(
        fan=frame[17],
        water=frame[19],
        volume=frame[20],
        carpet=bool(frame[28]),
        has_mop=bool(frame[27] & 1),
        work_mode=frame[16],
        # Area and time carry extra high bits in byte 33 (scaled by 255, as the app does)
        area=frame[18] + 255 * (frame[33] & 0x0F if len(frame) > 33 else 0),
        work_time=frame[23] + 255 * (frame[33] >> 4 if len(frame) > 33 else 0),
        fault_class=frame[25],
        fault_code=frame[26],
        child_lock=frame[46] == 1 if len(frame) > 47 else None,
    )


def parse_dnd(hex_frame: str | None) -> DoNotDisturb | None:
    if (frame := _reply(hex_frame, _QUERY_DND, 17)) is None:
        return None
    try:
        return DoNotDisturb(
            enabled=bool(frame[12]), start=time(frame[13], frame[14]), end=time(frame[15], frame[16])
        )
    except ValueError:
        return None


def parse_voice(hex_frame: str | None) -> int | None:
    if (frame := _reply(hex_frame, _QUERY_VOICE, 12)) is None:
        return None
    return frame[11]


def parse_auto_update(hex_frame: str | None) -> bool | None:
    """Whether the robot installs firmware updates by itself (byte 12: 0 off, 1 on)."""
    if (frame := _reply(hex_frame, _QUERY_AUTO_UPDATE[:2], 13)) is None or frame[12] > 1:
        return None
    return frame[12] == 1


def parse_wifi(hex_frame: str | None) -> WifiInfo | None:
    """Read the IP (4 bytes), signal (minus dBm), SSID length and SSID.

    The app reads them from byte 11, which would overlap the 35 16 echo; until a
    live reply confirms it, take the data from byte 12 when the echo is there.
    """
    if (frame := _reply(hex_frame, _QUERY_WIFI[:1], 18)) is None:
        return None
    at = 12 if frame[11] == _QUERY_WIFI[1] else 11
    length = frame[at + 5] if len(frame) > at + 5 else 0
    ssid = frame[at + 6 : at + 6 + length]
    if not length or len(ssid) != length:
        return None
    return WifiInfo(
        ip=".".join(str(b) for b in frame[at : at + 4]),
        ssid=ssid.decode("utf-8", "replace"),
        rssi=-frame[at + 4],
    )


def parse_schedules(hex_frame: str | None) -> list[Schedule] | None:
    """Read the schedule list: 30-byte entries from byte 13 (the last ends in the checksum)."""
    if (frame := _reply(hex_frame, _QUERY_SCHEDULES, 13)) is None:
        return None
    schedules: list[Schedule] = []
    for offset in range(13, len(frame) - 9, _SCHEDULE_ENTRY):
        week, hour, minute, duration, mode, fan, water, task_id, state = frame[offset : offset + 9]
        if task_id == 0:
            break
        if state > 1:  # 2 = invalid
            continue
        try:
            at = time(hour, minute)
        except ValueError:
            continue
        schedules.append(
            Schedule(
                task_id=task_id,
                days=tuple(day for day in range(7) if week & (1 << day)),
                repeat=bool(week & 0x80),
                start=at,
                duration=duration or 30,
                work_mode=mode,
                fan=fan,
                water=water,
                enabled=state == 0,
            )
        )
    return schedules

