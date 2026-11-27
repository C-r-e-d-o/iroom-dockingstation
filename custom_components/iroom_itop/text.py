"""Text-Parameter: Netzwerk (IP, Hostname …), PIN, Zugangscode.

Schreiben sendet cmd:<name>:<wert>; – Persistenz erst nach „Einstellungen
speichern" (save_changes) bzw. automatisch nach settings_delay.
"""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.text import TextEntity, TextMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ItopCoordinator
from .entity import ItopEntity

_IP = r"^((25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(25[0-5]|2[0-4]\d|1?\d?\d)$"


@dataclass(frozen=True)
class TextDesc:
    key: str
    name: str
    mode: TextMode = TextMode.TEXT
    pattern: str | None = None
    min: int = 0
    max: int = 32
    write_only: bool = False
    hint: str | None = None
    dhcp_locked: bool = False   # bei DHCP nicht editierbar (kommt vom DHCP-Server)


TEXTS = [
    # Network, ordered. "Network 1 · Mode" (DHCP/Static IP) is a select (select.py).
    TextDesc("host_name", "2 · Network Hostname", max=32),
    TextDesc("ip", "3 · Network IP address", pattern=_IP, min=7, max=15, dhcp_locked=True),
    TextDesc("subnet_mask", "4 · Network Subnet mask", pattern=_IP, min=7, max=15, dhcp_locked=True),
    TextDesc("dns", "5 · Network DNS", pattern=_IP, min=7, max=15, dhcp_locked=True),
    TextDesc("router", "6 · Network Gateway", pattern=_IP, min=7, max=15, dhcp_locked=True),
    TextDesc("port", "7 · Network Port", pattern=r"^\d{1,5}$", min=1, max=5),
    # PIN, Seriennummer und Access code sind nur lesbar -> Sensoren (sensor.py).
    # (accesscode ist über LAN weder les- noch setzbar; nur default_accesscode ist lesbar.)
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            add: AddEntitiesCallback) -> None:
    coord: ItopCoordinator = hass.data[DOMAIN][entry.entry_id]
    add(ItopText(coord, entry.entry_id, d) for d in TEXTS)


class ItopText(ItopEntity, TextEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coord, entry_id, desc: TextDesc):
        super().__init__(coord, entry_id, desc.key)
        self._d = desc
        self._attr_name = desc.name
        self._attr_mode = desc.mode
        self._attr_native_min = desc.min
        self._attr_native_max = desc.max
        if desc.pattern:
            self._attr_pattern = desc.pattern

    def _dhcp_active(self) -> bool:
        # connection_type == "1" is DHCP (verified on hardware; see select.py).
        return self._d.dhcp_locked and self.coordinator.inf("connection_type") == "1"

    @property
    def extra_state_attributes(self):
        if self._dhcp_active():
            return {"hint": "Assigned by the DHCP server — switch '1 · Network Mode' "
                            "to 'Static IP' to change this."}
        return {"hint": self._d.hint} if self._d.hint else None

    @property
    def native_value(self) -> str | None:
        if self._d.write_only:
            return None  # z. B. accesscode ist nicht auslesbar
        return self.coordinator.inf(self._d.key)

    async def async_set_value(self, value: str) -> None:
        # Im DHCP-Modus werden diese Werte vom DHCP-Server vergeben -> Änderung ablehnen.
        if self._dhcp_active():
            raise HomeAssistantError(
                "Not editable in DHCP mode — this value is assigned by the DHCP server. "
                "Switch '1 · Network Mode' to 'Static IP' first.")
        # build_cmd validiert IP/PIN/Text; bei Fehler wirft es -> HA zeigt Fehler
        await self.coordinator.client.cmd(self._d.key, value)
        if not self._d.write_only:
            await self.coordinator.client.readback(self._d.key)
