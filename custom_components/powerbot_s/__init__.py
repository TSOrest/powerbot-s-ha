"""Samsung VR7700 / POWERbot-S integration for Home Assistant.

Reverse-engineered from the POWERbot-S Android app (com.mzbots.android.powerbot v1.2.1).
Cloud API: mzrobo.com (built on Midea/MzBots platform).

This integration controls the robot via the cloud API (no local API found on the device).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .api import PowerBotApiClient, PowerBotApiError
from .const import (
    DOMAIN,
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_REGION,
    CONF_DEVICE_ID,
    CONF_ACCESS_TOKEN,
    CONF_REFRESH_TOKEN,
)
from .coordinator import PowerBotDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.VACUUM, Platform.SENSOR, Platform.BINARY_SENSOR]
SCAN_INTERVAL = timedelta(seconds=30)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
      """Set up POWERbot-S from a config entry."""
      client = PowerBotApiClient(
          email=entry.data[CONF_EMAIL],
          password=entry.data[CONF_PASSWORD],
          region=entry.data[CONF_REGION],
          access_token=entry.data.get(CONF_ACCESS_TOKEN),
          refresh_token=entry.data.get(CONF_REFRESH_TOKEN),
      )

    # Authenticate (will use stored token or re-login)
      try:
                await client.async_authenticate()
except PowerBotApiError as err:
        raise ConfigEntryNotReady(f"Cannot connect to POWERbot-S API: {err}") from err

    coordinator = PowerBotDataUpdateCoordinator(
              hass=hass,
              client=client,
              device_id=entry.data[CONF_DEVICE_ID],
              update_interval=SCAN_INTERVAL,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
      """Unload a config entry."""
      if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
                hass.data[DOMAIN].pop(entry.entry_id)
            return unload_ok
