"""Numerische Konfig-Parameter (Zeiten, Helligkeit, Empfindlichkeit …)."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, PARAM_NUMBER_META
from .coordinator import ItopCoordinator
from .entity import ItopEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            add: AddEntitiesCallback) -> None:
    coord: ItopCoordinator = hass.data[DOMAIN][entry.entry_id]
    add(
        ItopNumber(coord, entry.entry_id, key, unit, lo, hi)
        for key, (unit, lo, hi) in PARAM_NUMBER_META.items()
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
