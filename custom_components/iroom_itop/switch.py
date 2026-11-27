"""Schalter: Relais + verifizierte boolsche Bedien-Parameter.

Nur beschreibbare bool-Parameter aus WRITABLE_BOOL_PARAMS werden als Schalter
angeboten. Ungeprüfte Installer-/Motor-Booleans erscheinen read-only als
Diagnose-Sensoren (sensor.py), bis sie am echten Dock verifiziert sind.
"""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, WRITABLE_BOOL_PARAMS
from .coordinator import ItopCoordinator
from .entity import ItopEntity

# Relay: command open/close/toggle, state inf:relay0 = opened/closed
# (relay_ext is a bool parameter per the app -> handled by ItopBoolParam)
RELAYS = {"relay0": "Relay"}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            add: AddEntitiesCallback) -> None:
    coord: ItopCoordinator = hass.data[DOMAIN][entry.entry_id]
    ents: list[SwitchEntity] = [
        ItopRelay(coord, entry.entry_id, key, name) for key, name in RELAYS.items()
    ]
    for p in WRITABLE_BOOL_PARAMS:
        if p == "enable_audio_output":
            # right after the iPad buttons (Controls section), English name
            ents.append(ItopBoolParam(coord, entry.entry_id, p,
                                      name="Enable iPad Audio Output", category=None))
        else:
            ents.append(ItopBoolParam(coord, entry.entry_id, p))
    add(ents)


class ItopRelay(ItopEntity, SwitchEntity):
    def __init__(self, coord, entry_id, key, name):
        super().__init__(coord, entry_id, key)
        self._attr_name = name

    @property
    def is_on(self) -> bool | None:
        v = self.coordinator.inf(self._key)
        if v is None:
            return None
        return v.lower() in ("closed", "close", "1", "on")

    async def async_turn_on(self, **_):
        await self.coordinator.client.cmd(self._key, "close")
        await self.coordinator.client.readback(self._key)

    async def async_turn_off(self, **_):
        await self.coordinator.client.cmd(self._key, "open")
        await self.coordinator.client.readback(self._key)


class ItopBoolParam(ItopEntity, SwitchEntity):
    def __init__(self, coord, entry_id, key, name=None, category=EntityCategory.CONFIG):
        super().__init__(coord, entry_id, key)
        self._attr_name = name or key.replace("_", " ").capitalize()
        if category is not None:
            self._attr_entity_category = category

    @property
    def is_on(self) -> bool | None:
        v = self.coordinator.inf(self._key)
        if v is None:
            return None
        return v in ("1", "true", "on")

    async def async_turn_on(self, **_):
        await self.coordinator.client.cmd(self._key, "1")
        await self.coordinator.client.readback(self._key)

    async def async_turn_off(self, **_):
        await self.coordinator.client.cmd(self._key, "0")
        await self.coordinator.client.readback(self._key)
