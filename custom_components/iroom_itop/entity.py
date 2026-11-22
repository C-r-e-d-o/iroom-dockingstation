"""Basisklasse für alle iTop-Entitäten (gemeinsames Gerät + Verfügbarkeit)."""
from __future__ import annotations

try:  # Lage von DeviceInfo variiert je nach HA-Version
    from homeassistant.helpers.device_registry import DeviceInfo
except ImportError:  # ältere HA-Versionen
    from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL, DEFAULT_NAME
from .coordinator import ItopCoordinator


class ItopEntity(CoordinatorEntity[ItopCoordinator]):
    """Gemeinsame Basis: hängt alle Entitäten unter EIN Gerät."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ItopCoordinator, entry_id: str, key: str) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._key = key
        self._attr_unique_id = f"{entry_id}_{key}"
        mac = coordinator.inf("mac")
        serial = coordinator.inf("serial_nr")
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=DEFAULT_NAME,
            manufacturer=MANUFACTURER,
            model=MODEL,
            connections={("mac", mac)} if mac else set(),
            sw_version=coordinator.inf("dock_fw"),
            serial_number=serial,
        )

    @property
    def available(self) -> bool:
        return self.coordinator.available
