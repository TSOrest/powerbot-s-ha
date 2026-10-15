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


Box = tuple[int, int, int, int]


@dataclass(frozen=True)
class Overlays:
    """Virtual walls (x1 y1 x2 y2) and no-go / no-mop zones (two corners)."""

    walls: tuple[Box, ...] = ()
    no_go: tuple[Box, ...] = ()
    no_mop: tuple[Box, ...] = ()


def parse_boxes(text: Any) -> tuple[Box, ...]:
    """Groups of four grid coordinates from a "line ..." or "forbid_zone ..." string."""
    if isinstance(text, str) and text.startswith('"'):
        try:
            text = json.loads(text)
        except ValueError:
            return ()
    if not isinstance(text, str):
        return ()
    numbers = [int(token) for token in text.split() if token.lstrip("-").isdigit()]
    return tuple(
        (numbers[i], numbers[i + 1], numbers[i + 2], numbers[i + 3])
        for i in range(0, len(numbers) - 3, 4)
    )


_NO_GO = (230, 60, 60)
_NO_MOP = (60, 150, 230)
_VIRTUAL_WALL = (200, 30, 30)


def render_png(
    grid: Grid,
    room_map: bool | None = None,
    overlays: Overlays | None = None,
    scale: int = 2,
) -> bytes:
    """Draw the grid as an RGBA PNG with y up; rooms are coloured on a room map."""
    if room_map is None:
        room_map = grid.pixels[:1] == bytes([ROOM_MAP_MARK])
    width, height = grid.width, grid.height
    palette: dict[int, bytes] = {}
    image = bytearray()
    for y in range(height - 1, -1, -1):  # image rows go top-down
        for value in grid.pixels[y * width : (y + 1) * width]:
            if (pixel := palette.get(value)) is None:
                rgb = _colour(value, room_map)
                pixel = palette[value] = bytes((*rgb, 255)) if rgb else b"\0\0\0\0"
            image += pixel

    def put(x: int, y: int, rgb: tuple[int, int, int], alpha: float) -> None:
        col, row = x - grid.left, height - 1 - (y - grid.bottom)
        if 0 <= col < width and 0 <= row < height:
            i = 4 * (row * width + col)
            if image[i + 3] == 0:  # outside the map: just the overlay colour
                image[i : i + 3] = bytes(rgb)
            else:
                for c in range(3):
                    image[i + c] = round(rgb[c] * alpha + image[i + c] * (1 - alpha))
            image[i + 3] = max(image[i + 3], round(255 * alpha))

    if overlays:
        for zones, rgb in ((overlays.no_mop, _NO_MOP), (overlays.no_go, _NO_GO)):
            for x1, y1, x2, y2 in zones:
                top = grid.bottom + height - 1
                right = grid.left + width - 1
                for y in range(max(min(y1, y2), grid.bottom), min(max(y1, y2), top) + 1):
                    for x in range(max(min(x1, x2), grid.left), min(max(x1, x2), right) + 1):
                        edge = x in (x1, x2) or y in (y1, y2)
                        put(x, y, rgb, 1.0 if edge else 0.35)
        for x1, y1, x2, y2 in overlays.walls:
            steps = min(max(abs(x2 - x1), abs(y2 - y1), 1), 4 * (width + height))
            for step in range(steps + 1):
                put(
                    round(x1 + (x2 - x1) * step / steps),
                    round(y1 + (y2 - y1) * step / steps),
                    _VIRTUAL_WALL,
                    1.0,
                )

    rows = []
    for row in range(height):
        line = image[4 * row * width : 4 * (row + 1) * width]
        if scale > 1:
            line = b"".join(line[i : i + 4] * scale for i in range(0, len(line), 4))
        rows.extend([b"\0" + bytes(line)] * scale)
    return _png(width * scale, height * scale, b"".join(rows))


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
