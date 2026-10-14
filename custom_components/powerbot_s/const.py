"""Constants for the POWERbot-S integration."""

DOMAIN = "powerbot_s"

# Config entry keys
CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_REGION = "region"
CONF_DEVICE_ID = "device_id"
CONF_ACCESS_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"

# API credentials extracted from APK (com.mzbots.android.powerbot v1.2.1)
CLIENT_ID = "ef3450cd49484b40a0a1438ef3a47cb9"
APP_SECRET = "1537b2f65f1c69f528d0e973"

# Regional API hosts
REGION_HOSTS = {
    "na": "https://naprod.mzrobo.com",
    "eu": "https://euprod.mzrobo.com",
    "cn": "https://api.mzbots.com",
    "global": "https://global.mzrobo.com",
}

DEFAULT_REGION = "eu"

# App headers (replicated from AppIdLangRequestIdInterceptor)
APP_VERSION = "1.2.1.26101001"
APP_ENV = "release"

# Robot state values returned by shadow/device/state API
ROBOT_STATE_CLEANING = "cleaning"
ROBOT_STATE_PAUSED = "paused"
ROBOT_STATE_DOCKED = "charging"
ROBOT_STATE_RETURNING = "returning"
ROBOT_STATE_IDLE = "idle"
ROBOT_STATE_ERROR = "error"

# Supported vacuum features
ATTR_BATTERY_LEVEL = "battery_level"
ATTR_STATUS = "status"
ATTR_FAN_SPEED = "fan_speed"
