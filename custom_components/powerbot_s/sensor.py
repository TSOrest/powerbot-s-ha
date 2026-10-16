"""Sensor platform for POWERbot-S."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfArea,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONSUMABLES, FAN_SPEEDS, FAULT_OPTIONS, WORK_MODES, fault_key
from .coordinator import PowerBotConfigEntry, PowerBotDataUpdateCoordinator
from .entity import PowerBotEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class PowerBotSensorDescription(SensorEntityDescription):
    """Describes a POWERbot-S sensor."""

    value_fn: Callable[[PowerBotDataUpdateCoordinator], Any]
    # Needs data only a supported model provides (robot queries, consumables)
    robot: bool = False


def _connection(coordinator: PowerBotDataUpdateCoordinator) -> str:
    if coordinator.last_update_success and coordinator.data.get("connected", True):
        return "online"
    return "offline"


SENSORS: tuple[PowerBotSensorDescription, ...] = (
    PowerBotSensorDescription(
        key="status",
        translation_key="status",
        value_fn=lambda c: c.data.get("state"),
    ),
    PowerBotSensorDescription(
        key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda c: c.data.get("batteryLevel"),
    ),
    PowerBotSensorDescription(
        key="fan_speed",
        translation_key="fan_speed",
        device_class=SensorDeviceClass.ENUM,
        options=FAN_SPEEDS,
        value_fn=lambda c: c.fan_speed,
    ),
    PowerBotSensorDescription(
        key="connection",
        translation_key="connection",
        device_class=SensorDeviceClass.ENUM,
        options=["online", "offline"],
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_connection,
    ),
    PowerBotSensorDescription(
        key="cleaning_mode",
        translation_key="cleaning_mode",
        device_class=SensorDeviceClass.ENUM,
        options=list(WORK_MODES.values()),
        robot=True,
        value_fn=lambda c: WORK_MODES.get(c.work.work_mode) if c.work else None,
    ),
    PowerBotSensorDescription(
        key="cleaned_area",
        translation_key="cleaned_area",
        native_unit_of_measurement=UnitOfArea.SQUARE_METERS,
        robot=True,
        value_fn=lambda c: c.work.area if c.work else None,
    ),
    PowerBotSensorDescription(
        key="cleaning_time",
        translation_key="cleaning_time",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        robot=True,
        value_fn=lambda c: c.work.work_time if c.work else None,
    ),
    PowerBotSensorDescription(
        key="robot_error",
        translation_key="robot_error",
        device_class=SensorDeviceClass.ENUM,
        options=FAULT_OPTIONS,
        robot=True,
        value_fn=lambda c: fault_key(c.work.fault_class, c.work.fault_code) if c.work else None,
    ),
    PowerBotSensorDescription(
        key="error_code",
        translation_key="error_code",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        robot=True,
        value_fn=lambda c: f"{c.work.fault_class}.{c.work.fault_code}" if c.work else None,
    ),
    PowerBotSensorDescription(
        key="total_cleaning_time",
        translation_key="total_cleaning_time",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        suggested_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        robot=True,
        value_fn=lambda c: c.totals.get("worktime"),
    ),
    PowerBotSensorDescription(
        key="total_cleaned_area",
        translation_key="total_cleaned_area",
        native_unit_of_measurement=UnitOfArea.SQUARE_METERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        robot=True,
        value_fn=lambda c: c.totals.get("area"),
    ),
    PowerBotSensorDescription(
        key="total_cleanings",
        translation_key="total_cleanings",
        state_class=SensorStateClass.TOTAL_INCREASING,
        robot=True,
        value_fn=lambda c: int(c.totals["count"]) if "count" in c.totals else None,
    ),
    PowerBotSensorDescription(
        key="last_clean",
        translation_key="last_clean",
        device_class=SensorDeviceClass.TIMESTAMP,
        robot=True,
        value_fn=lambda c: c.last_clean,
    ),
    PowerBotSensorDescription(
        key="sensor_cleaning",
        translation_key="sensor_cleaning",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.MEASUREMENT,
        robot=True,
        value_fn=lambda c: c.sensor_hours,
    ),
    PowerBotSensorDescription(
        key="wifi_ssid",
        translation_key="wifi_ssid",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        robot=True,
        value_fn=lambda c: c.wifi.ssid if c.wifi else None,
    ),
    PowerBotSensorDescription(
        key="ip_address",
        translation_key="ip_address",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        robot=True,
        value_fn=lambda c: c.wifi.ip if c.wifi else None,
    ),
    PowerBotSensorDescription(
        key="wifi_signal",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        robot=True,
        value_fn=lambda c: c.wifi.rssi if c.wifi else None,
    ),
    *(
        PowerBotSensorDescription(
            key=f"{key}_life",
            translation_key=f"{key}_life",
            native_unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            robot=True,
            value_fn=lambda c, key=key: c.parts.get(key),
        )
        for key, _ in CONSUMABLES.values()
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PowerBotConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensor entities."""
    coordinator = entry.runtime_data
    async_add_entities(
        PowerBotSensor(coordinator, description)
        for description in SENSORS
        if coordinator.supported or not description.robot
    )


class PowerBotSensor(PowerBotEntity, SensorEntity):
    """A POWERbot-S sensor."""

    entity_description: PowerBotSensorDescription

    def __init__(
        self,
        coordinator: PowerBotDataUpdateCoordinator,
        description: PowerBotSensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def available(self) -> bool:
        # The connection sensor reports "offline" instead of becoming unavailable.
        return self.entity_description.key == "connection" or super().available

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator)
