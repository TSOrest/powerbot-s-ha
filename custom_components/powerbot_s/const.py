"""Constants for the POWERbot-S integration."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "powerbot_s"

MANUFACTURER = "Samsung"
MODEL = "POWERbot-S (VR7700)"

# Config entry keys (email / password come from homeassistant.const)
CONF_REGION = "region"
CONF_DEVICE_ID = "device_id"
CONF_ACCESS_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"

SCAN_INTERVAL = timedelta(seconds=30)

# mzrobo.com / MzBots API client id (from APK)
CLIENT_ID = "ef3450cd49484b40a0a1438ef3a47cb9"

# Regional API hosts
REGION_HOSTS = {
    "eu":     "https://euprod.mzrobo.com",
    "na":     "https://naprod.mzrobo.com",
    "global": "https://global.mzrobo.com",
    "cn":     "https://api.mzbots.com",
}
DEFAULT_REGION = "eu"

# App metadata (from APK manifest)
APP_VERSION = "1.2.1.26101001"
APP_ENV = "release"

# Fan speed mapping: API "fanLevel" value → fan speed option
FAN_LEVEL_MAP: dict[str, str] = {"1": "quiet", "2": "normal", "3": "strong"}
FAN_SPEEDS = ["quiet", "normal", "strong"]

# Substrings of the cloud "state" value, grouped by meaning
CLEANING_STATES = ("cleaning", "sweeping", "mopping", "spot", "wall_follow")
PAUSED_STATES = ("pause",)
DOCKED_STATES = ("charging", "docked")
RETURNING_STATES = ("returning", "going_home")
IDLE_STATES = ("idle", "standby")
ERROR_STATES = ("error", "fault")
