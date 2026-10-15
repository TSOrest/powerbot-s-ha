"""Decode the robot's map and rooms, and draw the map as a PNG.

Formats from the app's map plugin (M7 decoder). Both strings are space
separated and end in a base64, zlib-compressed grid of width x height bytes,
row 0 at the bottom:
  map:   <tag> <t0> <left> <bottom> <right> <top> <payload>
  rooms: <tag> <p0> <p1> <left> <bottom> <right> <top> <N> [<id> l b r t]xN <payload>
All coordinates are in the robot's map grid units.
"""
from __future__ import annotations

import base64
import binascii
import json
import struct
import zlib
from dataclasses import dataclass
from typing import Any

UNEXPLORED = 248
ROOM_MAP_MARK = 0xAA
ROOM_WALLS = (99, 255)
ROOM_NONE = 100
MAX_GRID = 4096 * 4096

# Room maps the app treats as "no rooms yet"
_EMPTY_ROOM_MAPS = (
    "4920 4920 4920 4920",
    "400 400 400 400 0",
    "map_zone 0 0 0 0 0 0 0",
    "map_zone 1 1 0 0 0 0 0",
)

_FLOOR = (225, 232, 240)
_WALL = (60, 90, 160)
_ROOM_COLOURS = (
    (255, 205, 160),
    (170, 220, 190),
    (180, 200, 245),
    (245, 190, 210),
    (215, 200, 245),
    (245, 230, 160),
)


@dataclass(frozen=True)
class Grid:
    left: int
    bottom: int
    width: int
    height: int
    pixels: bytes  # row 0 = bottom


def _inflate(payload: str, width: int, height: int) -> bytes | None:
    if width <= 0 or height <= 0 or width * height > MAX_GRID:
        return None
    payload = payload.replace("-", "+").replace("_", "/")
    payload += "=" * (-len(payload) % 4)
    try:
        data = zlib.decompress(base64.b64decode(payload))
    except (binascii.Error, ValueError, zlib.error):
        return None
    if len(data) < width * height:
        return None
    return data[: width * height]


def _ints(tokens: list[str]) -> list[int] | None:
    try:
        return [int(token) for token in tokens]
    except ValueError:
        return None


def decode_map(text: Any) -> Grid | None:
    """Decode the whole-map string; None if it is missing or malformed."""
    if not isinstance(text, str):
        return None
    tokens = text.split()
    if len(tokens) < 7 or (box := _ints(tokens[2:6])) is None:
        return None
    left, bottom, right, top = box
    width, height = right - left + 1, top - bottom + 1
    if (pixels := _inflate(tokens[-1], width, height)) is None:
        return None
    return Grid(left, bottom, width, height, pixels)


def decode_rooms(text: Any) -> tuple[Grid | None, list[int]]:
    """Decode the room map; return the grid and the room ids it lists."""
    if not isinstance(text, str) or any(empty in text for empty in _EMPTY_ROOM_MAPS):
        return None, []
    tokens = text.split()
    if len(tokens) < 9 or (head := _ints(tokens[3:8])) is None:
        return None, []
    left, bottom, right, top, count = head
    boxes = _ints(tokens[8 : 8 + 5 * count]) if count > 0 else []
    if boxes is None or len(boxes) != 5 * count:
        return None, []
    ids = [boxes[i] for i in range(0, len(boxes), 5)]
    width, height = right - left + 1, top - bottom + 1
    pixels = _inflate(tokens[-1], width, height)
    grid = Grid(left, bottom, width, height, pixels) if pixels else None
    return grid, ids


def room_names(ids: list[int], name_info: Any) -> dict[int, str]:
    """Room id -> name, from the roomNameInfo JSON; unnamed rooms get "Room N"."""
    names: dict[str, Any] = {}
    if isinstance(name_info, str):
        try:
            name_info = json.loads(name_info)
        except ValueError:
            name_info = None
    if isinstance(name_info, dict):
        names = {str(key): value for key, value in name_info.items()}
    return {
        room_id: str(names.get(str(room_id)) or f"Room {room_id}") for room_id in ids
    }


def _colour(value: int, room_map: bool) -> tuple[int, int, int] | None:
    if room_map:
        if value in ROOM_WALLS:
            return _WALL
        if 1 <= value <= 98:
            return _ROOM_COLOURS[value % len(_ROOM_COLOURS)]
        if 100 <= value <= 199:
            return _FLOOR
        if value and value % 16 == 0:  # some firmware stores id << 4
            return _ROOM_COLOURS[(value >> 4) % len(_ROOM_COLOURS)]
        return None
    if value == UNEXPLORED or value == 0:
        return None
    if value & 2:
        return _WALL
    if value & 1:
        return _FLOOR
    return None


def render_png(grid: Grid, room_map: bool | None = None, scale: int = 2) -> bytes:
    """Draw the grid as an RGBA PNG with y up; rooms are coloured on a room map."""
    if room_map is None:
        room_map = grid.pixels[:1] == bytes([ROOM_MAP_MARK])
    palette: dict[int, bytes] = {}
    rows = []
    for y in range(grid.height - 1, -1, -1):  # PNG rows go top-down
        line = bytearray()
        for value in grid.pixels[y * grid.width : (y + 1) * grid.width]:
            if (pixel := palette.get(value)) is None:
                rgb = _colour(value, room_map)
                pixel = palette[value] = bytes((*rgb, 255)) if rgb else b"\0\0\0\0"
            line += pixel * scale
        rows.extend([b"\0" + bytes(line)] * scale)
    return _png(grid.width * scale, grid.height * scale, b"".join(rows))


def _png(width: int, height: int, raw: bytes) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw, 6))
        + chunk(b"IEND", b"")
    )
