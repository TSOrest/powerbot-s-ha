"""Image platform for POWERbot-S: the map from the app."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import PowerBotConfigEntry, PowerBotDataUpdateCoordinator
from .entity import PowerBotEntity
from .robot_map import render_png

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PowerBotConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the map image."""
    coordinator = entry.runtime_data
    if coordinator.supported:
        async_add_entities([PowerBotMap(hass, coordinator)])


class PowerBotMap(PowerBotEntity, ImageEntity):
    """The map, with rooms coloured once the robot has split it into rooms."""

    _attr_translation_key = "map"
    _attr_content_type = "image/png"

    def __init__(self, hass: HomeAssistant, coordinator: PowerBotDataUpdateCoordinator) -> None:
        PowerBotEntity.__init__(self, coordinator, "map")
        ImageEntity.__init__(self, hass)
        self._png: bytes | None = None
        self._drawn: datetime | None = None

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.map_updated is not None

    @property
    def image_last_updated(self) -> datetime | None:
        return self.coordinator.map_updated

    @property
    def extra_state_attributes(self) -> dict[str, dict[int, str]]:
        return {"rooms": self.coordinator.rooms}

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_image_last_updated = self.coordinator.map_updated
        super()._handle_coordinator_update()

    async def async_image(self) -> bytes | None:
        coordinator = self.coordinator
        if coordinator.map_updated is None:
            return None
        if self._png is None or self._drawn != coordinator.map_updated:
            grid = coordinator.room_grid or coordinator.map_grid
            room_map = coordinator.room_grid is not None
            self._png = await self.hass.async_add_executor_job(render_png, grid, room_map)
            self._drawn = coordinator.map_updated
        return self._png
