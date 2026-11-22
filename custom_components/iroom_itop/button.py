"""Buttons: Einmal-Aktionen (Beep, Reboot, Speichern, iPad, Dock-Toggle)."""
from __future__ import annotations

from collections.abc import Callable, Awaitable

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ItopCoordinator
from .entity import ItopEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            add: AddEntitiesCallback) -> None:
    coord: ItopCoordinator = hass.data[DOMAIN][entry.entry_id]
    c = coord.client

    IPAD_HINT = "Only works when 'Audio output' is enabled."
    # (key, name, action, diagnostic, hint)
    defs: list[tuple] = [
        ("beep", "Beep", lambda: c.cmd("beep", 50), False, None),
        ("dock_toggle", "Toggle dock", lambda: c.cmd("idock", "toggle"), False, None),
        ("ipad_wakeup", "iPad Display On (needs audio output enable)", lambda: c.cmd("ipad", "wakeup"), False, IPAD_HINT),
        ("ipad_sleep", "iPad Display Off (needs audio output enable)", lambda: c.cmd("ipad", "sleep"), False, IPAD_HINT),
        ("save_changes", "Save settings", lambda: c.cmd("save_changes", 1), True, None),
        ("reboot", "Reboot", lambda: c.req("reboot"), True, None),
    ]
    add(ItopButton(coord, entry.entry_id, k, n, fn, diag, hint)
        for k, n, fn, diag, hint in defs)


class ItopButton(ItopEntity, ButtonEntity):
    def __init__(self, coord, entry_id, key, name, action, diagnostic, hint=None):
        super().__init__(coord, entry_id, key)
        self._attr_name = name
        self._action = action
        self._hint = hint
        if diagnostic:
            self._attr_entity_category = EntityCategory.CONFIG

    @property
    def extra_state_attributes(self):
        return {"hint": self._hint} if self._hint else None

    async def async_press(self) -> None:
        await self._action()
