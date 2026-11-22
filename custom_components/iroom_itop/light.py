"""LEDs der iTop (led0 = Home, led1..6 = Touch-Tasten, via iBezel).

Befehl: cmd:ledN:<0..100>;  (0 = aus). Zustand aus inf:ledN, falls geliefert.
"""
from __future__ import annotations

from homeassistant.components.light import ColorMode, LightEntity, ATTR_BRIGHTNESS
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, LED_COUNT
from .coordinator import ItopCoordinator
from .entity import ItopEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            add: AddEntitiesCallback) -> None:
    coord: ItopCoordinator = hass.data[DOMAIN][entry.entry_id]
    add(ItopLed(coord, entry.entry_id, i) for i in range(LED_COUNT))


class ItopLed(ItopEntity, LightEntity):
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    def __init__(self, coord, entry_id, idx):
        super().__init__(coord, entry_id, f"led{idx}")
        self._idx = idx
        self._attr_name = "LED Home" if idx == 0 else f"LED {idx}"
        self._optimistic = 0  # letzter gesetzter Prozentwert

    @property
    def extra_state_attributes(self):
        if self._idx == 0:
            return None
        return {"hint": f"When off, button {self._idx} does not work."}

    def _pct(self) -> int | None:
        v = self.coordinator.inf(self._key)
        if v is None:
            return self._optimistic
        try:
            return max(0, min(100, int(float(v))))
        except (ValueError, TypeError):
            return self._optimistic

    @property
    def is_on(self) -> bool:
        return (self._pct() or 0) > 0

    @property
    def brightness(self) -> int | None:
        pct = self._pct()
        return round(pct * 255 / 100) if pct is not None else None

    async def async_turn_on(self, **kwargs):
        if ATTR_BRIGHTNESS in kwargs:
            pct = round(kwargs[ATTR_BRIGHTNESS] * 100 / 255)
        else:
            pct = self._optimistic or 100
        pct = max(1, min(100, pct))
        self._optimistic = pct
        await self.coordinator.client.cmd(self._key, pct)
        await self.coordinator.client.readback(self._key)

    async def async_turn_off(self, **_):
        self._optimistic = 0
        await self.coordinator.client.cmd(self._key, 0)
        await self.coordinator.client.readback(self._key)
