"""Fixtures for POWERbot-S tests."""
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
    ):
        yield {
            "login": login,
            "devices": devices,
            "state": state,
            "send": send,
            "voices": voices,
            "parts": parts,
        }


@pytest.fixture
def domain():
    return DOMAIN
