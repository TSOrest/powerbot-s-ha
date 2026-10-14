"""DataUpdateCoordinator for POWERbot-S."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PowerBotApiClient, PowerBotApiError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class PowerBotDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator to manage fetching POWERbot-S state from cloud."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: PowerBotApiClient,
        device_id: str,
        update_interval: timedelta,
    ) -> None:
        self.client = client
        self.device_id = device_id

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{device_id}",
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> dict:
        """Fetch data from the API."""
        try:
            state = await self.client.async_get_device_state(self.device_id)
            if state is None:
                _LOGGER.warning(
                    "No state returned for device %s", self.device_id
                )
                return {}
            return state
        except PowerBotApiError as err:
            raise UpdateFailed(f"Error communicating with POWERbot API: {err}") from err
