"""Event-Entitäten: Tastendrücke (button0..6) und IR-Ereignisse.

Das Dock sendet unaufgefordert Ereignisse (als evn:/inf:). Diese werden über
den Dispatcher an die passende Event-Entität verteilt.
"""
from __future__ import annotations

from homeassistant.components.event import EventEntity, EventDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, BTN_COUNT, SIGNAL_EVENT
from .coordinator import ItopCoordinator
from .entity import ItopEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            add: AddEntitiesCallback) -> None:
    coord: ItopCoordinator = hass.data[DOMAIN][entry.entry_id]
    ents: list[EventEntity] = [
        ItopButtonEvent(coord, entry.entry_id, i) for i in range(BTN_COUNT)
    ]
    ents.append(ItopIrEvent(coord, entry.entry_id))
    add(ents)


class _ItopEventBase(ItopEntity, EventEntity):
    _attr_device_class = EventDeviceClass.BUTTON

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        signal = f"{SIGNAL_EVENT}_{self._entry_id}"
        self.async_on_remove(
            async_dispatcher_connect(self.hass, signal, self._handle)
        )

    @callback
    def _handle(self, name: str, value: str) -> None:
        if name != self._key:
            return
        event_type = (value or "trigger").strip().lower()
        if self.event_types and event_type not in self.event_types:
            event_type = self.event_types[0]
        self._trigger_event(event_type)
        self.async_write_ha_state()


class ItopButtonEvent(_ItopEventBase):
    _attr_event_types = ["pushed", "released"]

    def __init__(self, coord, entry_id, idx):
        super().__init__(coord, entry_id, f"button{idx}")
        self._idx = idx
        if idx == 0:
            self._attr_name = "Home button"
        else:
            self._attr_name = f"Button {idx} (needs LED {idx} on)"

    @property
    def extra_state_attributes(self):
        if self._idx == 0:
            return None
        return {"hint": f"Only works when LED {self._idx} is on."}


class ItopIrEvent(_ItopEventBase):
    _attr_event_types = ["irevent"]

    def __init__(self, coord, entry_id):
        super().__init__(coord, entry_id, "irevent")
        self._attr_name = "IR event"
