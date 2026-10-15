"""Map decoding, drawing and room cleaning tests."""
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
import pytest

from custom_components.powerbot_s import protocol, robot_map

from .conftest import MAP, ROOM_NAMES, ROOMS
from .test_init import _entry


def test_decode_map() -> None:
    grid = robot_map.decode_map(MAP)
    assert (grid.left, grid.bottom, grid.width, grid.height) == (10, 20, 4, 3)
    assert grid.pixels[5:7] == bytes([1, 1])
    assert robot_map.decode_map("map 0 1 2") is None
    assert robot_map.decode_map("map 0 0 0 3 3 notbase64!") is None
    assert robot_map.decode_map(None) is None


def test_decode_rooms() -> None:
    grid, ids = robot_map.decode_rooms(ROOMS)
    assert ids == [1, 2]
    assert grid.pixels[5:7] == bytes([1, 2])
    assert robot_map.room_names(ids, ROOM_NAMES) == {1: "Kitchen", 2: "Hall"}
    assert robot_map.room_names([3], None) == {3: "Room 3"}
    assert robot_map.decode_rooms("map_zone 0 0 0 0 0 0 0") == (None, [])


def test_render_png() -> None:
    png = robot_map.render_png(robot_map.decode_map(MAP), scale=1)
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    assert int.from_bytes(png[16:20], "big") == 4
    assert int.from_bytes(png[20:24], "big") == 3


def test_clean_rooms_frame() -> None:
    frame = bytes.fromhex(protocol.clean_rooms(2, 2, [(1, 1), (3, 2)]))
    body = frame[10:-1]
    assert body[:10] == bytes([0x22, 0x02, 0, 2, 0, 0x0A, 2, 0, 2, 0])
    assert body[10:14] == bytes([1, 1, 3, 2])
    assert len(body) == 30 and not any(body[14:])


async def test_map_image_and_rooms(hass: HomeAssistant, hass_client, mock_api) -> None:
    entry = _entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    image = hass.states.get("image.kitchen_map")
    assert image.attributes["rooms"] == {1: "Kitchen", 2: "Hall"}
    client = await hass_client()
    resp = await client.get(image.attributes["entity_picture"])
    assert resp.status == 200
    assert (await resp.read()).startswith(b"\x89PNG")
    assert hass.states.get("vacuum.kitchen").attributes["rooms"] == {1: "Kitchen", 2: "Hall"}

    await hass.services.async_call(
        "vacuum",
        "send_command",
        {"entity_id": "vacuum.kitchen", "command": "clean_rooms", "params": {"rooms": ["hall", 1]}},
        blocking=True,
    )
    mock_api["send"].assert_any_await(
        "111", protocol.clean_rooms(3, 2, [(2, 1), (1, 1)]), wait_timeout=15
    )
    with pytest.raises(ServiceValidationError, match="Unknown room"):
        await hass.services.async_call(
            "vacuum",
            "send_command",
            {"entity_id": "vacuum.kitchen", "command": "clean_rooms", "params": {"rooms": ["Attic"]}},
            blocking=True,
        )
