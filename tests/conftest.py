"""Fixtures for POWERbot-S tests."""
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.powerbot_s.const import DOMAIN

STATE = {"id": "111", "state": "charging_finish", "batteryLevel": 87, "fanLevel": "3", "connected": True}


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
            AsyncMock(return_value=[{"deviceId": "111", "nickname": "Kitchen"}]),
        ) as devices,
        patch(
            "custom_components.powerbot_s.api.PowerBotApiClient.async_get_device_state",
            AsyncMock(return_value=dict(STATE)),
        ) as state,
        patch("custom_components.powerbot_s.api.PowerBotApiClient.async_send_command", AsyncMock()) as send,
    ):
        yield {"login": login, "devices": devices, "state": state, "send": send}


@pytest.fixture
def domain():
    return DOMAIN
