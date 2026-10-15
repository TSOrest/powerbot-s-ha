"""DataUpdateCoordinator for POWERbot-S."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PowerBotApiClient, PowerBotApiError, PowerBotAuthError
from .const import CONF_DEVICE_ID, DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

type PowerBotConfigEntry = ConfigEntry[PowerBotDataUpdateCoordinator]


class PowerBotDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls the robot's state from the cloud."""

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

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            state = await self.client.async_get_device_state(self.device_id)
        except PowerBotAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except PowerBotApiError as err:
            raise UpdateFailed(f"Error communicating with POWERbot-S cloud: {err}") from err
        if state is None:
            raise UpdateFailed(f"No state returned for device {self.device_id}")
        return state
