"""Binäre Sensoren: Eingänge, Docking, Netzwerkstatus."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorEntity, BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DI_COUNT
from .coordinator import ItopCoordinator
from .entity import ItopEntity

_TRUE = ("1", "on", "true", "closed", "high", "docked", "connected", "established")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            add: AddEntitiesCallback) -> None:
    coord: ItopCoordinator = hass.data[DOMAIN][entry.entry_id]
    ents: list[BinarySensorEntity] = [
        ItopBinary(coord, entry.entry_id, f"digital{i}", f"Input {i}",
                   BinarySensorDeviceClass.OPENING)
        for i in range(DI_COUNT)
    ]
    ents.append(ItopDocking(coord, entry.entry_id))
    ents.append(ItopBinary(coord, entry.entry_id, "network_connected", "Network connected",
                           BinarySensorDeviceClass.CONNECTIVITY, EntityCategory.DIAGNOSTIC))
    ents.append(ItopBinary(coord, entry.entry_id, "network_established", "Network established",
                           BinarySensorDeviceClass.CONNECTIVITY, EntityCategory.DIAGNOSTIC))
    ents.append(ItopBinary(coord, entry.entry_id, "unsaved_changes", "Unsaved changes",
                           None, EntityCategory.DIAGNOSTIC))
    add(ents)


class ItopBinary(ItopEntity, BinarySensorEntity):
    def __init__(self, coord, entry_id, key, name, dev_class=None, cat=None):
        super().__init__(coord, entry_id, key)
        self._attr_name = name
        self._attr_device_class = dev_class
        if cat:
            self._attr_entity_category = cat

    @property
    def is_on(self) -> bool | None:
        v = self.coordinator.inf(self._key)
        if v is None:
            return None
        return v.strip().lower() in _TRUE


class ItopDocking(ItopEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PLUG

    def __init__(self, coord, entry_id):
        super().__init__(coord, entry_id, "dockingstate")
        self._attr_name = "iPad docked"

    @property
    def is_on(self) -> bool | None:
        v = self.coordinator.inf("dockingstate")
        if v is None:
            return None
        return v.strip().lower() == "docked"
