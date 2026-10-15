"""Text platform for POWERbot-S: room names."""
from __future__ import annotations

from homeassistant.components.text import TextEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import PowerBotConfigEntry, PowerBotDataUpdateCoordinator
from .entity import PowerBotEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PowerBotConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add a name field for each room on the map, as rooms appear."""
    coordinator = entry.runtime_data
    if not coordinator.supported:
        return
    known: set[int] = set()

    @callback
    def _add_rooms() -> None:
        new = set(coordinator.rooms) - known
        known.update(new)
        async_add_entities(PowerBotRoomName(coordinator, room_id) for room_id in sorted(new))

    _add_rooms()
    entry.async_on_unload(coordinator.async_add_listener(_add_rooms))


class PowerBotRoomName(PowerBotEntity, TextEntity):
    """A room's name; the app shows the same name."""

    _attr_translation_key = "room_name"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min = 1
    _attr_native_max = 20

    def __init__(self, coordinator: PowerBotDataUpdateCoordinator, room_id: int) -> None:
        super().__init__(coordinator, f"room_{room_id}_name")
        self._room_id = room_id
        self._attr_translation_placeholders = {"room": str(room_id)}

    @property
    def available(self) -> bool:
        return super().available and self._room_id in self.coordinator.rooms

    @property
    def native_value(self) -> str | None:
        return self.coordinator.rooms.get(self._room_id)

    async def async_set_value(self, value: str) -> None:
        name = value.strip()
        if not name:
            raise ServiceValidationError("The room name cannot be empty")
        await self.coordinator.async_rename_room(self._room_id, name)
