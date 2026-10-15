"""Fixtures for POWERbot-S tests."""
import base64
import zlib
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.powerbot_s.const import DOMAIN

from custom_components.powerbot_s import protocol

STATE = {"id": "111", "state": "charging_finish", "batteryLevel": 87, "fanLevel": "3", "connected": True}

# Robot replies recorded from a real VR7700 (volume 99, carpet on, DND 22:00-08:00 on, voice 128)
REPLIES = {
    protocol.query_work_state(): "aa30b800000000000103320106000200080100036301630001000001010001010100000100000201d1030a00000000001e",
    protocol.query_dnd(): "aa11b80000000000000332050116000800de",
    protocol.query_voice(): "aa0cb800000000000103368082",
    # One schedule: every day 10:00, 30 min, whole house, normal/normal, task 1, off
    protocol.query_schedules(): "aa2ab800000000000003340100ff0a001e08020201010000000000000000000000000000000000000000b1",
}
VOICES = [
    {"id": 35, "voiceIndex": 35, "title": "English", "defaultVoice": 1},
    {"id": 128, "voiceIndex": 128, "title": "Українська", "defaultVoice": 0},
]
DEVICE = {
    "deviceId": "111",
    "nickname": "Kitchen",
    "ownerId": "u1",
    "product": {"sn8": "610VR510", "productModel": "VR7700", "protoVersion": 0},
    "panel": {"name": "T0xB8_610VR510", "versionName": "2.2.46"},
}
PARTS = {"filter_net_time": "4112", "side_brush_time": "4112", "roll_brush_time": "4112"}


async def _send(device_id, frame, wait_timeout=None):
    return REPLIES.get(frame)


def _grid(left: int, bottom: int, rows: list[list[int]]) -> tuple[str, str]:
    """Return the box and payload of a map string, rows given bottom first."""
    width, height = len(rows[0]), len(rows)
    payload = base64.b64encode(zlib.compress(bytes(v for row in rows for v in row))).decode()
    return f"{left} {bottom} {left + width - 1} {bottom + height - 1}", payload


# 4x3 map: walls round a 2x1 floor
_BOX, _PAYLOAD = _grid(10, 20, [[2, 2, 2, 2], [2, 1, 1, 2], [2, 2, 2, 2]])
MAP = f"map 0 {_BOX} {_PAYLOAD}"
# Same box split into rooms 1 and 2
_RBOX, _RPAYLOAD = _grid(10, 20, [[99, 99, 99, 99], [99, 1, 2, 99], [99, 99, 99, 99]])
ROOMS = f"map_zone 0 0 {_RBOX} 2 1 11 21 11 21 2 12 21 12 21 {_RPAYLOAD}"
ROOM_NAMES = '{"1": "Kitchen", "2": "Hall"}'


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Allow loading custom_components in every test."""
    return


@pytest.fixture
def mock_api():
    """Patch the cloud client used by the config flow and the integration."""
    with (
        patch("custom_components.powerbot_s.api.PowerBotApiClient.async_login", AsyncMock()) as login,
        patch(
            "custom_components.powerbot_s.api.PowerBotApiClient.async_get_devices",
            AsyncMock(return_value=[dict(DEVICE)]),
        ) as devices,
        patch(
            "custom_components.powerbot_s.api.PowerBotApiClient.async_get_device_state",
            AsyncMock(return_value=dict(STATE)),
        ) as state,
        patch(
            "custom_components.powerbot_s.api.PowerBotApiClient.async_send_command",
            AsyncMock(side_effect=_send),
        ) as send,
        patch(
            "custom_components.powerbot_s.api.PowerBotApiClient.async_get_voices",
            AsyncMock(return_value=VOICES),
        ) as voices,
        patch(
            "custom_components.powerbot_s.api.PowerBotApiClient.async_get_parts",
            AsyncMock(return_value=dict(PARTS)),
        ) as parts,
        patch(
            "custom_components.powerbot_s.api.PowerBotApiClient.async_get_map",
            AsyncMock(return_value=MAP),
        ) as robot_map,
        patch(
            "custom_components.powerbot_s.api.PowerBotApiClient.async_get_rooms",
            AsyncMock(return_value=(ROOMS, ROOM_NAMES)),
        ) as rooms,
    ):
        yield {
            "login": login,
            "devices": devices,
            "state": state,
            "send": send,
            "voices": voices,
            "parts": parts,
            "map": robot_map,
            "rooms": rooms,
        }


@pytest.fixture
def domain():
    return DOMAIN
