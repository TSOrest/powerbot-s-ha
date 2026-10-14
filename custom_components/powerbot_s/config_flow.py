"""Config flow for POWERbot-S integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from .api import PowerBotApiClient, PowerBotApiError, PowerBotAuthError
from .const import (
    DOMAIN,
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_DEVICE_ID,
    CONF_REGION,
    CONF_ACCESS_TOKEN,
    CONF_REFRESH_TOKEN,
    DEFAULT_REGION,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

STEP_DEVICE_ID_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE_ID): str,
    }
)


async def validate_credentials(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate credentials and return tokens."""
    client = PowerBotApiClient(
        email=data[CONF_EMAIL],
        password=data[CONF_PASSWORD],
    )
    try:
        await client.async_authenticate()
        tokens = client.get_tokens()
        try:
            devices = await client.async_get_devices()
        except PowerBotApiError:
            devices = []
    finally:
        await client.async_close()

    return {"devices": devices, "tokens": tokens}


async def validate_device_id(hass: HomeAssistant, tokens: dict, device_id: str) -> dict:
    """Verify that device_id is reachable via shadow state API."""
    client = PowerBotApiClient(
        email="",
        password="",
        region=tokens.get("region", DEFAULT_REGION),
        access_token=tokens.get("access_token"),
        refresh_token=tokens.get("refresh_token"),
    )
    try:
        state = await client.async_get_device_state(device_id)
        return state or {}
    finally:
        await client.async_close()


class PowerBotConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow for POWERbot-S."""

    VERSION = 1

    def __init__(self) -> None:
        self._email: str | None = None
        self._password: str | None = None
        self._tokens: dict = {}
        self._devices: list[dict] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ):
        """Handle the initial step — collect email/password."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                result = await validate_credentials(self.hass, user_input)
            except PowerBotAuthError:
                errors["base"] = "invalid_auth"
            except PowerBotApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception during config flow")
                errors["base"] = "unknown"
            else:
                self._email = user_input[CONF_EMAIL]
                self._password = user_input[CONF_PASSWORD]
                self._tokens = result["tokens"]
                self._devices = result["devices"]
                return await self.async_step_device_id()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_device_id(
        self, user_input: dict[str, Any] | None = None
    ):
        """Ask user for device ID."""
        errors: dict[str, str] = {}

        hint_device_id = ""
        hint_name = ""
        if self._devices:
            first = self._devices[0]
            hint_device_id = str(first.get("deviceId") or first.get("id", ""))
            hint_name = first.get("nickname") or first.get("name") or ""

        if user_input is not None:
            device_id = user_input[CONF_DEVICE_ID].strip()
            if not device_id:
                errors[CONF_DEVICE_ID] = "cannot_connect"
            else:
                try:
                    state = await validate_device_id(self.hass, self._tokens, device_id)
                except PowerBotApiError:
                    errors["base"] = "cannot_connect"
                except Exception:
                    _LOGGER.exception("Unexpected exception validating device ID")
                    errors["base"] = "unknown"
                else:
                    if state:
                        if hint_name and hint_device_id == device_id:
                            title = hint_name
                        else:
                            title = f"POWERbot-S {device_id[-6:]}"

                        await self.async_set_unique_id(device_id)
                        self._abort_if_unique_id_configured()

                        return self.async_create_entry(
                            title=title,
                            data={
                                CONF_EMAIL: self._email,
                                CONF_PASSWORD: self._password,
                                CONF_DEVICE_ID: device_id,
                                CONF_REGION: self._tokens.get("region", DEFAULT_REGION),
                                CONF_ACCESS_TOKEN: self._tokens.get("access_token"),
                                CONF_REFRESH_TOKEN: self._tokens.get("refresh_token"),
                            },
                        )
                    else:
                        errors["base"] = "cannot_connect"

        if hint_device_id:
            hint_text = hint_device_id
        else:
            hint_text = "1870169732145270786"

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_DEVICE_ID,
                    default=hint_device_id if hint_device_id else vol.UNDEFINED,
                ): str,
            }
        )

        return self.async_show_form(
            step_id="device_id",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "hint": hint_text,
            },
        )
