"""Numerische Konfig-Parameter (beschreibbar nur, wo verifiziert).

Nur Parameter aus WRITABLE_NUMBER_PARAMS werden als beschreibbare number-Entität
angeboten (aktuell nur Display-Helligkeit mit 0..100). Ungeprüfte Timer-/Motor-
Werte (jam_factor, settings_delay, close_time …) erscheinen read-only als
Diagnose-Sensoren (sensor.py), bis sie am echten Dock verifiziert sind.
"""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, PARAM_NUMBER_META, WRITABLE_NUMBER_PARAMS
from .coordinator import ItopCoordinator
from .entity import ItopEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            add: AddEntitiesCallback) -> None:
    coord: ItopCoordinator = hass.data[DOMAIN][entry.entry_id]
    add(
        ItopNumber(coord, entry.entry_id, key, *PARAM_NUMBER_META[key])
        for key in WRITABLE_NUMBER_PARAMS
    )


class ItopNumber(ItopEntity, NumberEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX

    def __init__(self, coord, entry_id, key, unit, lo, hi):
        super().__init__(coord, entry_id, key)
        self._attr_name = key.replace("_", " ").capitalize()
        self._attr_native_unit_of_measurement = unit
        self._attr_native_min_value = lo
        self._attr_native_max_value = hi
        self._attr_native_step = 1

    @property
    def native_value(self) -> float | None:
        v = self.coordinator.inf(self._key)
        if v is None or v == "":
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.client.cmd(self._key, int(value))
        await self.coordinator.client.readback(self._key)
