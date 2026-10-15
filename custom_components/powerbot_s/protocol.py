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

_LOCATE = bytes([0x35, 0x07, 0, 0, 0, 0, 0])
_QUERY_WORK_STATE = bytes([0x32, 0x01])
_QUERY_DND = bytes([0x32, 0x05])
_QUERY_VOICE = bytes([0x36])

_WORK_MODE_AUTO = 0x08


def build_frame(body: bytes, msg_type: int = _MSG_CONTROL) -> str:
    """Wrap a body into a full frame and return it as upper-case hex."""
    frame = bytearray([0xAA, 0x0A + len(body), _DEVICE_TYPE, 0, 0, 0, 0, 0, 0, msg_type])
    frame += body
    frame.append(-sum(frame[1:]) & 0xFF)
    return frame.hex().upper()


def start(fan: int, water: int) -> str:
    """Start an automatic clean with the given suction and water levels."""
    return build_frame(bytes([_CONTROL, _START, 0, 2, 0, _WORK_MODE_AUTO, fan, 0, water, 0, 0]))


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


@dataclass(frozen=True)
class WorkState:
    """Settings read from the work-state reply (type 0x03, body 32 01)."""

    fan: int
    water: int
    volume: int
    carpet: bool
    has_mop: bool


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
