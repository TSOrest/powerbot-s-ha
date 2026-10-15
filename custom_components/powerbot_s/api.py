"""API client for the POWERbot-S / mzrobo.com cloud platform.

Reverse-engineered from com.mzbots.android.powerbot v1.2.1 APK.

- Login: POST /auth/login/email-password?clientId=<CLIENT_ID>
  Body: {"email": "...", "password": "..."}
  Returns: {"data": {"accessToken": "...", "refreshToken": "...", ...}}
- Refresh: GET /auth/refresh-token?refreshToken=<token>
- Devices: GET /app/devices?version=1&isShared=false
- State: GET /shadow/device/state?devices=<deviceId>
- Command: POST /devices/commands/<deviceId>  Body: {"data": "<hex>"}
"""
from __future__ import annotations

from collections.abc import Callable
import logging
from typing import Any
import uuid

import aiohttp

from .const import APP_ENV, APP_VERSION, CLIENT_ID, DEFAULT_REGION, REGION_HOSTS

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=15)

# Login error codes returned by mzrobo.com
_WRONG_REGION_CODES = ("0051204", "0051213")
_BAD_CREDENTIALS_CODES = ("0051001", "0051002", "0051004")


class PowerBotApiError(Exception):
    """General API error."""


class PowerBotAuthError(PowerBotApiError):
    """Authentication error (wrong credentials or expired session)."""


def device_id_of(device: dict[str, Any]) -> str:
    """Return the device id from a device list item."""
    return str(device.get("deviceId") or device.get("id") or "")


def device_name_of(device: dict[str, Any]) -> str:
    """Return a human readable name from a device list item."""
    return device.get("nickname") or device.get("name") or "POWERbot-S"


class PowerBotApiClient:
    """Client for the mzrobo.com / POWERbot-S cloud API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        email: str,
        password: str,
        region: str = DEFAULT_REGION,
        access_token: str | None = None,
        refresh_token: str | None = None,
        on_tokens_updated: Callable[[dict[str, str | None]], None] | None = None,
    ) -> None:
        self._session = session
        self._email = email
        self._password = password
        self._region = region if region in REGION_HOSTS else DEFAULT_REGION
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._on_tokens_updated = on_tokens_updated

    @property
    def _base_url(self) -> str:
        return REGION_HOSTS[self._region]

    def _make_headers(self) -> dict[str, str]:
        """Build request headers matching the Android app's interceptors."""
        headers = {
            "Accept-Language": "en",
            "nonce": uuid.uuid4().hex,
            "x-platform": "Android29",
            "x-app-version": APP_VERSION,
            "x-app-env": APP_ENV,
            "x-timezone-id": "UTC",
            "Content-Type": "application/json",
            "User-Agent": "okhttp/4.10.0",
        }
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        return headers

    async def _raw_request(self, method: str, url: str, **kwargs: Any) -> tuple[int, Any]:
        try:
            async with self._session.request(
                method, url, headers=self._make_headers(), timeout=REQUEST_TIMEOUT, **kwargs
            ) as resp:
                if resp.status == 401:
                    return resp.status, None
                return resp.status, await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise PowerBotApiError(f"Error talking to {url}: {err}") from err

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Make an authenticated API request, refreshing the token on 401."""
        if not self._access_token:
            await self.async_login()
        url = f"{self._base_url}{path}"
        status, data = await self._raw_request(method, url, **kwargs)
        if status == 401:
            _LOGGER.debug("Got 401, refreshing token")
            await self._refresh_access_token()
            status, data = await self._raw_request(method, url, **kwargs)
            if status == 401:
                raise PowerBotAuthError("Authentication failed after token refresh")
        return self._check_response(data)

    @staticmethod
    def _check_response(data: Any) -> Any:
        if not isinstance(data, dict):
            raise PowerBotApiError(f"Unexpected response: {data!r}")
        error_code = data.get("errorCode")
        if error_code and error_code != "0":
            reason = data.get("reason") or data.get("msg") or "Unknown error"
            raise PowerBotApiError(f"API error {error_code}: {reason}")
        return data.get("data", data)

    def _store_tokens(self, token_data: dict[str, Any]) -> None:
        self._access_token = token_data.get("accessToken")
        self._refresh_token = token_data.get("refreshToken") or self._refresh_token
        if self._on_tokens_updated:
            self._on_tokens_updated(self.get_tokens())

    async def async_login(self) -> None:
        """Log in with email/password, finding the account's region."""
        regions = [self._region] + [r for r in REGION_HOSTS if r != self._region]
        for region in regions:
            url = f"{REGION_HOSTS[region]}/auth/login/email-password?clientId={CLIENT_ID}"
            try:
                status, data = await self._raw_request(
                    "POST", url, json={"email": self._email, "password": self._password}
                )
            except PowerBotApiError as err:
                _LOGGER.debug("Login to region %s failed: %s", region, err)
                continue
            if status == 401 or not isinstance(data, dict):
                raise PowerBotAuthError("Login rejected")
            error_code = data.get("errorCode")
            if error_code in _WRONG_REGION_CODES:
                _LOGGER.debug("Account is not in region %s", region)
                continue
            if error_code in _BAD_CREDENTIALS_CODES:
                raise PowerBotAuthError(data.get("msg") or "Wrong email or password")
            if error_code and error_code != "0":
                raise PowerBotApiError(
                    f"Login failed ({error_code}): {data.get('reason') or data.get('msg')}"
                )
            self._region = region
            self._store_tokens(data.get("data") or {})
            if not self._access_token:
                raise PowerBotApiError("Login response did not contain a token")
            _LOGGER.debug("Logged in to mzrobo.com, region %s", region)
            return
        raise PowerBotAuthError("Account not found in any region")

    async def _refresh_access_token(self) -> None:
        """Refresh the access token, falling back to a full login."""
        if self._refresh_token:
            url = f"{self._base_url}/auth/refresh-token"
            status, data = await self._raw_request(
                "GET", url, params={"refreshToken": self._refresh_token}
            )
            if (
                status != 401
                and isinstance(data, dict)
                and data.get("errorCode") in (None, "0")
                and isinstance(data.get("data"), dict)
                and data["data"].get("accessToken")
            ):
                self._store_tokens(data["data"])
                return
        self._access_token = None
        await self.async_login()

    async def async_get_devices(self) -> list[dict[str, Any]]:
        """Return all robots on the account."""
        result = await self._request("GET", "/app/devices", params={"version": 1, "isShared": "false"})
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            for key in ("list", "devices", "items", "data"):
                if isinstance(result.get(key), list):
                    return result[key]
        return []

    async def async_get_device_state(self, device_id: str) -> dict[str, Any] | None:
        """Return the shadow state of a device (battery, status, ...)."""
        result = await self._request("GET", "/shadow/device/state", params={"devices": device_id})
        if isinstance(result, list):
            for item in result:
                if isinstance(item, dict) and str(item.get("id")) == str(device_id):
                    return item
            return None
        return result if isinstance(result, dict) else None

    async def async_send_command(
        self, device_id: str, hex_data: str, wait_timeout: int | None = None
    ) -> None:
        """Send a hex command to the device."""
        body: dict[str, Any] = {"data": hex_data}
        if wait_timeout is not None:
            body["waitTimeoutInSeconds"] = wait_timeout
        await self._request("POST", f"/devices/commands/{device_id}", json=body)

    def get_tokens(self) -> dict[str, str | None]:
        """Return the current session (for storage in the config entry)."""
        return {
            "access_token": self._access_token,
            "refresh_token": self._refresh_token,
            "region": self._region,
        }
