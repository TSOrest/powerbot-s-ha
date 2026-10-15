"""Config flow for POWERbot-S."""
from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import (
    PowerBotApiClient,
    PowerBotApiError,
    PowerBotAuthError,
    device_id_of,
    device_name_of,
)
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_DEVICE_ID,
    CONF_REFRESH_TOKEN,
    CONF_REGION,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

CREDENTIALS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): TextSelector(
            TextSelectorConfig(type=TextSelectorType.EMAIL, autocomplete="username")
        ),
        vol.Required(CONF_PASSWORD): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD, autocomplete="current-password")
        ),
    }
)


class PowerBotConfigFlow(ConfigFlow, domain=DOMAIN):
    """Sign in to the POWERbot-S cloud and pick a robot."""

    VERSION = 1

    def __init__(self) -> None:
        self._credentials: dict[str, Any] = {}
        self._tokens: dict[str, str | None] = {}
        self._devices: dict[str, str] = {}  # device id -> name
        self._client: PowerBotApiClient | None = None

    async def _async_login(self, email: str, password: str) -> PowerBotApiClient:
        client = PowerBotApiClient(
            session=async_get_clientsession(self.hass), email=email, password=password
        )
        await client.async_login()
        return client

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the POWERbot-S app account."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                client = await self._async_login(
                    user_input[CONF_EMAIL], user_input[CONF_PASSWORD]
                )
                devices = await client.async_get_devices()
            except PowerBotAuthError:
                errors["base"] = "invalid_auth"
            except PowerBotApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during sign in")
                errors["base"] = "unknown"
            else:
                self._credentials = user_input
                self._tokens = client.get_tokens()
                configured = self._async_current_ids(include_ignore=False)
                self._devices = {
                    device_id_of(d): device_name_of(d)
                    for d in devices
                    if device_id_of(d) and device_id_of(d) not in configured
                }
                if not devices:
                    # Device list came back empty: fall back to entering the id by hand.
                    self._client = client
                    return await self.async_step_manual()
                if not self._devices:
                    return self.async_abort(reason="already_configured")
                if len(self._devices) == 1:
                    return await self._async_create(next(iter(self._devices)))
                return await self.async_step_select_device()

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(CREDENTIALS_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_select_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user pick a robot when the account has several."""
        if user_input is not None:
            return await self._async_create(user_input[CONF_DEVICE_ID])

        options = [
            SelectOptionDict(value=device_id, label=f"{name} ({device_id})")
            for device_id, name in self._devices.items()
        ]
        return self.async_show_form(
            step_id="select_device",
            data_schema=vol.Schema(
                {vol.Required(CONF_DEVICE_ID): SelectSelector(SelectSelectorConfig(options=options))}
            ),
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the device id when the account's device list is empty."""
        errors: dict[str, str] = {}
        if user_input is not None and self._client is not None:
            device_id = user_input[CONF_DEVICE_ID].strip()
            try:
                state = await self._client.async_get_device_state(device_id)
            except PowerBotApiError:
                errors["base"] = "cannot_connect"
            else:
                if state:
                    return await self._async_create(device_id)
                errors["base"] = "device_not_found"

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema({vol.Required(CONF_DEVICE_ID): str}),
            errors=errors,
        )

    async def _async_create(self, device_id: str) -> ConfigFlowResult:
        await self.async_set_unique_id(device_id)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=self._devices.get(device_id, "POWERbot-S"),
            data={
                CONF_EMAIL: self._credentials[CONF_EMAIL],
                CONF_PASSWORD: self._credentials[CONF_PASSWORD],
                CONF_DEVICE_ID: device_id,
                CONF_REGION: self._tokens.get("region"),
                CONF_ACCESS_TOKEN: self._tokens.get("access_token"),
                CONF_REFRESH_TOKEN: self._tokens.get("refresh_token"),
            },
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start re-authentication when the stored login stops working."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the account password again."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                client = await self._async_login(
                    user_input[CONF_EMAIL], user_input[CONF_PASSWORD]
                )
                device_ids = {device_id_of(d) for d in await client.async_get_devices()}
            except PowerBotAuthError:
                errors["base"] = "invalid_auth"
            except PowerBotApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during re-authentication")
                errors["base"] = "unknown"
            else:
                if entry.data[CONF_DEVICE_ID] not in device_ids:
                    errors["base"] = "device_not_found"
                else:
                    tokens = client.get_tokens()
                    return self.async_update_reload_and_abort(
                        entry,
                        data_updates={
                            CONF_EMAIL: user_input[CONF_EMAIL],
                            CONF_PASSWORD: user_input[CONF_PASSWORD],
                            CONF_REGION: tokens["region"],
                            CONF_ACCESS_TOKEN: tokens["access_token"],
                            CONF_REFRESH_TOKEN: tokens["refresh_token"],
                        },
                    )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=self.add_suggested_values_to_schema(
                CREDENTIALS_SCHEMA, user_input or {CONF_EMAIL: entry.data[CONF_EMAIL]}
            ),
            errors=errors,
        )
