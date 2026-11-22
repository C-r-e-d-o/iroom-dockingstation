"""Dock-Mechanik als Cover (idock: open/close/toggle)."""
from __future__ import annotations

from homeassistant.components.cover import CoverEntity, CoverEntityFeature, CoverDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ItopCoordinator
from .entity import ItopEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            add: AddEntitiesCallback) -> None:
    coord: ItopCoordinator = hass.data[DOMAIN][entry.entry_id]
    add([ItopDockCover(coord, entry.entry_id)])


class ItopDockCover(ItopEntity, CoverEntity):
    _attr_device_class = CoverDeviceClass.DOOR
    _attr_supported_features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE

    def __init__(self, coord, entry_id):
        super().__init__(coord, entry_id, "idock")
        self._attr_name = "Dock"
        self._assumed = None  # True=offen, False=zu (optimistisch)

    @property
    def is_closed(self) -> bool | None:
        # Zustand kommt vom Antrieb (am echten Gerät bestätigt: platformdrive),
        # Befehl geht an idock. latchdrive als Fallback.
        v = self.coordinator.inf("platformdrive") or self.coordinator.inf("latchdrive") \
            or self.coordinator.inf("idock")
        if v in ("open", "opened", "opening"):
            return False
        if v in ("close", "closed", "closing"):
            return True
        return None if self._assumed is None else (not self._assumed)

    async def async_open_cover(self, **_):
        self._assumed = True
        await self.coordinator.client.cmd("idock", "open")

    async def async_close_cover(self, **_):
        self._assumed = False
        await self.coordinator.client.cmd("idock", "close")
