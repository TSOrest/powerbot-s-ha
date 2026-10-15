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

# Midea servers that hold consumable counters and the voice pack list
PARTS_HOSTS = {
    "eu": "https://api-euca.midea.com",
    "na": "https://api-ca.midea.com",
    "global": "https://api-euca.midea.com",
    "cn": "https://mx-cnca.midea.com",
}
DEFAULT_SN8 = "610VR510"

# Models whose control plugin (Midea M7, project m7MSLifeSamsung) the command
# frames come from: VR7700 for Europe and North America, protocol version 0.
SUPPORTED_SN8 = ("610VR510", "620VR520")
SUPPORTED_PROTO_VERSIONS = (0,)

# Work modes reported in the work-state reply (byte 16)
WORK_MODES = {
    1: "random",
    2: "arc",
    3: "edge",
    4: "spot",
    5: "spiral",
    6: "bed",
    7: "wide_spiral",
    8: "auto",
    9: "area",
    10: "room",
    11: "zone",
    12: "path",
}

# Consumables: Midea field name -> (entity key, lifetime in hours)
CONSUMABLES = {
    "filter_net_time": ("filter", 150),
    "side_brush_time": ("side_brush", 100),
    "roll_brush_time": ("main_brush", 200),
}

# App metadata (from APK manifest). The cloud only lists devices for x-app-env "prod".
APP_VERSION = "1.2.1.26101001"
APP_ENV = "prod"

# Suction levels as used by the robot (shadow "fanLevel" and command bytes)
FAN_LEVELS: dict[str, int] = {
    "off": 0,
    "quiet": 1,
    "low": 4,
    "normal": 2,
    "turbo": 3,
    "max": 5,
}
FAN_SPEEDS = list(FAN_LEVELS)
FAN_LEVEL_MAP: dict[str, str] = {str(v): k for k, v in FAN_LEVELS.items()}
DEFAULT_FAN = "turbo"

# Mop water levels (shadow "waterLevel" and command bytes)
WATER_LEVELS: dict[str, int] = {"off": 0, "low": 1, "normal": 2, "high": 3}
WATER_LEVEL_MAP: dict[str, str] = {str(v): k for k, v in WATER_LEVELS.items()}
DEFAULT_WATER = "normal"

# Cloud "state" values (names from the POWERbot-S app), grouped by meaning
STATE_CLEANING = "cleaning"
STATE_PAUSED = "paused"
STATE_RETURNING = "returning"
STATE_DOCKED = "docked"
STATE_IDLE = "idle"
STATE_ERROR = "error"

ROBOT_STATES: dict[str, str] = {
    "cleaning": STATE_CLEANING,
    "positioning": STATE_CLEANING,
    "discovering": STATE_CLEANING,
    "manual_control": STATE_CLEANING,
    "pause": STATE_PAUSED,
    "charging_pause": STATE_PAUSED,
    "wiping_pause": STATE_PAUSED,
    "charging_back": STATE_RETURNING,
    "wiping_back": STATE_RETURNING,
    "charging": STATE_DOCKED,
    "charging_finish": STATE_DOCKED,
    "on_station": STATE_DOCKED,
    "stop": STATE_IDLE,
    "sleep": STATE_IDLE,
    "upgrading": STATE_IDLE,
    "error": STATE_ERROR,
}


def robot_state(raw: str | None) -> str | None:
    """Group a raw cloud state string; unknown non-empty values count as idle."""
    if not raw:
        return None
    return ROBOT_STATES.get(raw.lower(), STATE_IDLE)
