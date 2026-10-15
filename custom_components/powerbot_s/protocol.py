"""Command frames for the POWERbot-S (VR7700).

Taken from the app's control plugin (T0xB8_610VR510 v2.2.46):
  AA <0x0A + len(body)> B8 00 00 00 00 00 00 <msg type> <body> <checksum>
Control commands use msg type 0x02 and a body starting with 0x22 and a
sub-command byte. The checksum is the two's complement of the byte sum
between the AA header and the checksum.
"""
from __future__ import annotations

_DEVICE_TYPE = 0xB8
_MSG_CONTROL = 0x02
_CONTROL = 0x22

_START = 0x02
_DOCK = 0x01
_STOP = 0x03
_PAUSE = 0x1B
_CONTINUE = 0x1C
_SET_SUCTION = 0x04
_CARPET = 0x0C

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
