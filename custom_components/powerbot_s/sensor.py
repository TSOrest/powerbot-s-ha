"""Sensor platform for POWERbot-S."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_DEVICE_ID, FAN_LEVEL_MAP
from .coordinator import PowerBotDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities."""
    coordinator: PowerBotDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        PowerBotStateSensor(coordinator, entry),
        PowerBotBatterySensor(coordinator, entry),
        PowerBotFanSpeedSensor(coordinator, entry),
        PowerBotConnectedSensor(coordinator, entry),
    ])


class _PowerBotSensorBase(
    CoordinatorEntity[PowerBotDataUpdateCoordinator], SensorEntity
):
    """Base class for POWERbot sensors."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PowerBotDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._device_id: str = entry.data[CONF_DEVICE_ID]

    @property
    def device_info(self) -> dict:
        return {"identifiers": {(DOMAIN, self._device_id)}}


class PowerBotStateSensor(_PowerBotSensorBase):
    """Raw state string from the cloud (e.g. 'cleaning', 'charging_finish')."""

    _attr_name = "Status"
    _attr_icon = "mdi:robot-vacuum"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"powerbot_{self._device_id}_status"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("state")

    @property
    def extra_state_attributes(self) -> dict:
        """Expose full data dict as extra attributes."""
        data = dict(self.coordinator.data)
        data.pop("state", None)
        data.pop("batteryLevel", None)
        return data


class PowerBotBatterySensor(_PowerBotSensorBase):
    """Battery level sensor."""

    _attr_name = "Battery"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:battery"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"powerbot_{self._device_id}_battery"

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.get("batteryLevel")


class PowerBotFanSpeedSensor(_PowerBotSensorBase):
    """Current fan / suction speed reported by the robot."""

    _attr_name = "Fan speed"
    _attr_icon = "mdi:fan"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"powerbot_{self._device_id}_fan_speed"

    @property
    def native_value(self) -> str | None:
        level = str(self.coordinator.data.get("fanLevel", "2"))
        return FAN_LEVEL_MAP.get(level, "normal")


class PowerBotConnectedSensor(_PowerBotSensorBase):
    """Connectivity state — online / offline."""

    _attr_name = "Connection"
    _attr_icon = "mdi:wifi"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"powerbot_{self._device_id}_connection"

    @property
    def native_value(self) -> str:
        """Return 'online' or 'offline' based on coordinator success."""
        if self.coordinator.last_update_success:
            connected = self.coordinator.data.get("connected", True)
            return "online" if connected else "offline"
        return "offline"
