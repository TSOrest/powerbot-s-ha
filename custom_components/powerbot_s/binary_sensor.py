"""Binary sensor platform for POWERbot-S."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_DEVICE_ID
from .coordinator import PowerBotDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# State strings that map to the "error" condition
_ERROR_STATES = {"error", "fault"}

# State strings considered "online/cleaning" for the cleaning binary sensor
_CLEANING_STATES = {
    "cleaning", "sweeping", "mopping", "spot", "auto_cleaning", "wall_follow"
}

# State strings considered "docked"
_DOCKED_STATES = {"charging_finish", "charging", "docked"}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor entities."""
    coordinator: PowerBotDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
          PowerBotErrorBinarySensor(coordinator, entry),
          PowerBotCleaningBinarySensor(coordinator, entry),
          PowerBotDockedBinarySensor(coordinator, entry),
          PowerBotOnlineBinarySensor(coordinator, entry),
    ])


class _PowerBotBinarySensorBase(
    CoordinatorEntity[PowerBotDataUpdateCoordinator], BinarySensorEntity
):
    """Base class for POWERbot binary sensors."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PowerBotDataUpdateCoordinator, entry: ConfigEntry) -> None:
              super().__init__(coordinator)
              self._device_id: str = entry.data[CONF_DEVICE_ID]

    @property
    def device_info(self) -> dict:
              return {"identifiers": {(DOMAIN, self._device_id)}}

    def _state_lower(self) -> str:
              return (self.coordinator.data.get("state") or "").lower()


class PowerBotErrorBinarySensor(_PowerBotBinarySensorBase):
    """True when the robot reports an error or fault state."""

    _attr_name = "Error"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:alert-circle"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
              super().__init__(coordinator, entry)
              self._attr_unique_id = f"powerbot_{self._device_id}_error"

    @property
    def is_on(self) -> bool:
              state = self._state_lower()
              return any(err in state for err in _ERROR_STATES)


class PowerBotCleaningBinarySensor(_PowerBotBinarySensorBase):
    """True when the robot is actively cleaning."""

    _attr_name = "Cleaning"
    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_icon = "mdi:robot-vacuum"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
              super().__init__(coordinator, entry)
              self._attr_unique_id = f"powerbot_{self._device_id}_cleaning"

    @property
    def is_on(self) -> bool:
              state = self._state_lower()
              return any(cs in state for cs in _CLEANING_STATES)


class PowerBotDockedBinarySensor(_PowerBotBinarySensorBase):
    """True when the robot is in the charging dock."""

    _attr_name = "Docked"
    _attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING
    _attr_icon = "mdi:home-battery"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
              super().__init__(coordinator, entry)
              self._attr_unique_id = f"powerbot_{self._device_id}_docked"

    @property
    def is_on(self) -> bool:
              state = self._state_lower()
              return any(ds in state for ds in _DOCKED_STATES)


class PowerBotOnlineBinarySensor(_PowerBotBinarySensorBase):
    """True when the coordinator was able to reach the cloud API on last poll."""

    _attr_name = "Online"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_icon = "mdi:cloud-check"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
              super().__init__(coordinator, entry)
              self._attr_unique_id = f"powerbot_{self._device_id}_online"

    @property
    def is_on(self) -> bool:
              return self.coordinator.last_update_success
      
