"""Base entity for POWERbot-S."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import PowerBotDataUpdateCoordinator


class PowerBotEntity(CoordinatorEntity[PowerBotDataUpdateCoordinator]):
    """Common device info and naming for all POWERbot-S entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PowerBotDataUpdateCoordinator, key: str | None) -> None:
        super().__init__(coordinator)
        device_id = coordinator.device_id
        # Unique ids match the ones used by earlier versions, so entities keep their history.
        self._attr_unique_id = f"powerbot_{device_id}" + (f"_{key}" if key else "")
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=coordinator.config_entry.title,
            manufacturer=MANUFACTURER,
            model=coordinator.model or MODEL,
            model_id=coordinator.sn8,
            serial_number=device_id,
            sw_version=(fw.installed if (fw := coordinator.firmware.get("firmware")) else None),
        )

    @property
    def state_str(self) -> str:
        """Lower-cased raw state string from the cloud."""
        return str(self.coordinator.data.get("state") or "").lower()
