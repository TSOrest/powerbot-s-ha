"""Samsung POWERbot-S (VR7700) integration for Home Assistant.

Talks to the mzrobo.com cloud used by the POWERbot-S mobile app.
"""
from __future__ import annotations

from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PowerBotApiClient
from .const import CONF_ACCESS_TOKEN, CONF_REFRESH_TOKEN, CONF_REGION, DEFAULT_REGION, DOMAIN
from .coordinator import PowerBotConfigEntry, PowerBotDataUpdateCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.IMAGE,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TIME,
    Platform.VACUUM,
]


async def async_setup_entry(hass: HomeAssistant, entry: PowerBotConfigEntry) -> bool:
    """Set up POWERbot-S from a config entry."""

    @callback
    def _save_tokens(tokens: dict[str, str | None]) -> None:
        """Persist refreshed tokens so a restart doesn't need a new login."""
        hass.config_entries.async_update_entry(
            entry,
            data={
                **entry.data,
                CONF_ACCESS_TOKEN: tokens["access_token"],
                CONF_REFRESH_TOKEN: tokens["refresh_token"],
                CONF_REGION: tokens["region"],
            },
        )

    client = PowerBotApiClient(
        session=async_get_clientsession(hass),
        email=entry.data[CONF_EMAIL],
        password=entry.data[CONF_PASSWORD],
        region=entry.data.get(CONF_REGION, DEFAULT_REGION),
        access_token=entry.data.get(CONF_ACCESS_TOKEN),
        refresh_token=entry.data.get(CONF_REFRESH_TOKEN),
        on_tokens_updated=_save_tokens,
    )

    coordinator = PowerBotDataUpdateCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    issue_id = f"unsupported_model_{coordinator.device_id}"
    if coordinator.supported:
        ir.async_delete_issue(hass, DOMAIN, issue_id)
    else:
        ir.async_create_issue(
            hass,
            DOMAIN,
            issue_id,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="unsupported_model",
            translation_placeholders={
                "name": entry.title,
                "model": coordinator.model or "?",
                "sn8": coordinator.sn8 or "?",
                "plugin": coordinator.plugin or "?",
            },
            learn_more_url="https://github.com/TSOrest/powerbot-s-ha/issues",
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: PowerBotConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
