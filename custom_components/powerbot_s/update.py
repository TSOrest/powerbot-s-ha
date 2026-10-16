"""Firmware update entities for POWERbot-S (show only; updates are installed from the app)."""
from __future__ import annotations

from homeassistant.components.update import UpdateDeviceClass, UpdateEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import PowerBotConfigEntry, PowerBotDataUpdateCoordinator
from .entity import PowerBotEntity

PARALLEL_UPDATES = 0

# The cloud only says that an update exists, usually without its version
NEW_VERSION = "new"

# Firmware part in the cloud reply -> entity key
PARTS = {"firmware": "firmware", "module": "wifi_module_firmware"}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PowerBotConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up firmware update entities."""
    coordinator = entry.runtime_data
    if coordinator.supported:
        async_add_entities(PowerBotUpdate(coordinator, part) for part in PARTS)


class PowerBotUpdate(PowerBotEntity, UpdateEntity):
    """Whether the cloud offers new firmware for the robot or its Wi-Fi module."""

    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PowerBotDataUpdateCoordinator, part: str) -> None:
        super().__init__(coordinator, PARTS[part])
        self._part = part
        self._attr_translation_key = PARTS[part]

    @property
    def installed_version(self) -> str | None:
        info = self.coordinator.firmware.get(self._part)
        return info.installed if info else None

    @property
    def latest_version(self) -> str | None:
        if (info := self.coordinator.firmware.get(self._part)) is None:
            return None
        if not info.update:
            return info.installed
        return info.latest if info.latest and info.latest != info.installed else NEW_VERSION

    @property
    def release_summary(self) -> str | None:
        info = self.coordinator.firmware.get(self._part)
        return info.notes[:255] if info and info.update and info.notes else None
