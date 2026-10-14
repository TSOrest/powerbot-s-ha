"""API client for the POWERbot-S / mzrobo.com cloud platform.

Reverse-engineered from com.mzbots.android.powerbot v1.2.1 APK.

Key findings:
- Login: POST /auth/login/email-password?clientId=<CLIENT_ID>
  Body: {"email": "...", "password": "..."}
  Returns: {"data": {"accessToken": "...", "refreshToken": "...", "expiresIn": ..., "tokenType": "..."}}

- Get devices: GET /app/devices?version=1&isShared=false
  Headers: Authorization: Bearer <accessToken>

- Get device state: GET /shadow/device/state?devices=<deviceId>
  Returns: {"data": [{"id": "...", "state": "...", "batteryLevel": ...}]}

- Send command: POST /devices/commands/<deviceId>
  Body: {"data": "<hex_string>"}
  The hex commands are proprietary binary protocol with CRC8 checksum.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

import aiohttp

from .const import (
    CLIENT_ID,
    REGION_HOSTS,
    APP_VERSION,
    APP_ENV,
)

_LOGGER = logging.getLogger(__name__)

# Timeout for API calls
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=15)


class PowerBotApiError(Exception):
    """General API error."""


class PowerBotAuthError(PowerBotApiError):
    """Authentication error."""


class PowerBotApiClient:
    """Client for the mzrobo.com / POWERbot-S cloud API."""

    def __init__(
        self,
        email: str,
        password: str,
        region: str = "eu",
        access_token: str | None = None,
        refresh_token: str | None = None,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._email = email
        self._password = password
        self._region = region
        self._base_url = REGION_HOSTS.get(region, REGION_HOSTS["eu"])
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._session = session
        self._owns_session = session is None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=REQUEST_TIMEOUT)
        return self._session

    def _make_headers(self) -> dict[str, str]:
        """Build request headers matching the Android app's interceptors."""
        headers = {
            "Accept-Language": "uk",
            "nonce": uuid.uuid4().hex,
            "x-platform": "Android29",
            "x-app-version": APP_VERSION,
            "x-app-env": APP_ENV,
            "x-timezone-id": "Europe/Kiev",
            "Content-Type": "application/json",
            "User-Agent": "okhttp/4.10.0",
        }
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make an API request, refreshing token on 401."""
        session = await self._get_session()
        url = f"{self._base_url}{path}"

        async with session.request(
            method,
            url,
            headers=self._make_headers(),
            **kwargs,
        ) as resp:
            if resp.status == 401:
                # Token expired — try to refresh
                _LOGGER.debug("Got 401, attempting token refresh")
                await self._refresh_access_token()
                # Retry with new token
                async with session.request(
                    method,
                    url,
                    headers=self._make_headers(),
                    **kwargs,
                ) as resp2:
                    if resp2.status == 401:
                        raise PowerBotAuthError("Authentication failed after token refresh")
                    data = await resp2.json()
                    return self._check_response(data)

            data = await resp.json(content_type=None)
            return self._check_response(data)

    def _check_response(self, data: dict) -> dict:
        """Check API response for errors."""
        if not isinstance(data, dict):
            raise PowerBotApiError(f"Unexpected response: {data}")
        # mzrobo API returns errors with errorCode field
        error_code = data.get("errorCode")
        if error_code and error_code != "0":
            reason = data.get("reason", data.get("msg", "Unknown error"))
            raise PowerBotApiError(f"API error {error_code}: {reason}")
        return data.get("data", data)

    async def async_authenticate(self) -> None:
        """Authenticate with email/password and store tokens."""
        if self._access_token:
            # We have a token — verify it works
            try:
                await self.async_get_devices()
                return
            except PowerBotAuthError:
                pass  # Token invalid, re-authenticate below
            except PowerBotApiError:
                pass  # Network or other error, try to use existing token

        _LOGGER.debug("Logging in to mzrobo.com as %s", self._email)
        session = await self._get_session()

        # Try EU first (most common for Ukraine), then NA, skip CN/global
        region_order = [
            ("eu", REGION_HOSTS["eu"]),
            ("na", REGION_HOSTS["na"]),
        ]
        for region_name, host in region_order:
            try:
                url = f"{host}/auth/login/email-password?clientId={CLIENT_ID}"
                async with session.post(
                    url,
                    headers=self._make_headers(),
                    json={"email": self._email, "password": self._password},
                ) as resp:
                    data = await resp.json(content_type=None)
                    error_code = data.get("errorCode")
                    if error_code in ("0051204", "0051213"):
                        # "0051204" = user not in this region
                        # "0051213" = account is in a different region (server tells us which)
                        # Check if server gave us the correct region
                        region_hint = data.get("data", {})
                        if isinstance(region_hint, dict) and region_hint.get("region"):
                            hint = region_hint["region"]
                            _LOGGER.debug(
                                "Server redirected account to region %s", hint
                            )
                            # If we haven't tried that region yet, skip to it
                            if hint in REGION_HOSTS and hint != region_name:
                                continue
                        _LOGGER.debug("User not in region %s, trying next", region_name)
                        continue
                    if error_code in ("0051004", "0051001", "0051002"):
                        # Wrong email or password
                        raise PowerBotAuthError(
                            f"Login failed ({error_code}): {data.get('msg', 'Wrong email or password')}"
                        )
                    if error_code and error_code != "0":
                        raise PowerBotAuthError(
                            f"Login failed ({error_code}): {data.get('reason', data.get('msg'))}"
                        )
                    token_data = data.get("data", {})
                    self._access_token = token_data.get("accessToken")
                    self._refresh_token = token_data.get("refreshToken")
                    self._base_url = host
                    self._region = region_name
                    _LOGGER.info("Authenticated with mzrobo.com, region: %s", region_name)
                    return
            except aiohttp.ClientError as err:
                _LOGGER.warning("Connection error for region %s: %s", region_name, err)
                continue

        raise PowerBotAuthError(
            "Could not find account in any region (NA, EU, CN). "
            "Check your email/password."
        )

    async def _refresh_access_token(self) -> None:
        """Refresh the access token using the refresh token."""
        if not self._refresh_token:
            raise PowerBotAuthError("No refresh token available, please re-authenticate")
        session = await self._get_session()
        url = f"{self._base_url}/auth/refresh-token?refreshToken={self._refresh_token}"
        async with session.get(url, headers=self._make_headers()) as resp:
            data = await resp.json(content_type=None)
            error_code = data.get("errorCode")
            if error_code and error_code != "0":
                # Refresh failed, try full re-login
                self._access_token = None
                await self.async_authenticate()
                return
            token_data = data.get("data", {})
            self._access_token = token_data.get("accessToken")
            self._refresh_token = token_data.get("refreshToken")
            _LOGGER.debug("Token refreshed successfully")

    async def async_get_devices(self) -> list[dict]:
        """Get all devices for the authenticated user.

        DeviceBean JSON fields (from APK @SerializedName annotations):
          "deviceId"  → device unique ID
          "nickname"  → user-set device name
          "connected" → online status (bool)
          "state"     → embedded StateBean (batteryLevel, state string)
        """
        result = await self._request("GET", "/app/devices?version=1&isShared=false")
        if isinstance(result, list):
            return result
        # Some API versions wrap the list
        if isinstance(result, dict):
            for key in ("list", "devices", "items", "data"):
                if key in result and isinstance(result[key], list):
                    return result[key]
        return []

    async def async_get_device_info(self, device_id: str) -> dict:
        """Get detailed info for a specific device."""
        return await self._request("GET", f"/devices/{device_id}")

    async def async_get_device_state(self, device_id: str) -> dict | None:
        """Get the shadow state of a device (battery, status, etc.)."""
        result = await self._request(
            "GET", f"/shadow/device/state?devices={device_id}"
        )
        # Returns a list of state objects; find the one for our device
        if isinstance(result, list):
            for item in result:
                if str(item.get("id")) == str(device_id):
                    return item
        return result if isinstance(result, dict) else None

    async def async_send_command(
        self, device_id: str, hex_data: str, wait_timeout: int | None = None
    ) -> None:
        """Send a hex command to the device via the cloud API.

        POST /devices/commands/{deviceId}
        Body: {"data": "<hex_string>", "waitTimeoutInSeconds": <int>}
        """
        body: dict[str, Any] = {"data": hex_data}
        if wait_timeout is not None:
            body["waitTimeoutInSeconds"] = wait_timeout
        await self._request("POST", f"/devices/commands/{device_id}", json=body)

    def get_tokens(self) -> dict[str, str | None]:
        """Return current auth tokens (for storage in config entry)."""
        return {
            "access_token": self._access_token,
            "refresh_token": self._refresh_token,
            "region": self._region,
        }

    async def async_close(self) -> None:
        """Close the HTTP session."""
        if self._owns_session and self._session and not self._session.closed:
            await self._session.close()
