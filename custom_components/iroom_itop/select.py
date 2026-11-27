"""Netzwerk-Modus: DHCP oder feste IP (Parameter connection_type)."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ItopCoordinator
from .entity import ItopEntity

# connection_type mapping, verified on hardware
# (model iDock_Q6_TouchDock_Mode, firmware 1.7.06):
#   DHCP       -> "1"
#   Static IP  -> "0"
# The parameter is an unsigned int, but only these two values are used; any other
# value maps to no option (current_option returns None, shown blank) and the two
# options below are the only ones that can be written.
_OPT_TO_VAL = {"DHCP": "1", "Static IP": "0"}
_VAL_TO_OPT = {v: k for k, v in _OPT_TO_VAL.items()}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            add: AddEntitiesCallback) -> None:
    coord: ItopCoordinator = hass.data[DOMAIN][entry.entry_id]
    add([ItopConnectionType(coord, entry.entry_id)])


class ItopConnectionType(ItopEntity, SelectEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_name = "1 · Network Mode"
    _attr_options = list(_OPT_TO_VAL.keys())

    def __init__(self, coord, entry_id):
        super().__init__(coord, entry_id, "connection_type")

    @property
    def current_option(self) -> str | None:
        return _VAL_TO_OPT.get(self.coordinator.inf("connection_type"))

    @property
    def extra_state_attributes(self):
        return {"hint": "DHCP = IP obtained automatically; Static IP = from the network "
                        "fields. Changing this may change the IP and drop the connection."}

    async def async_select_option(self, option: str) -> None:
        val = _OPT_TO_VAL.get(option)
        if val is None:
            return
        await self.coordinator.client.cmd("connection_type", val)
        await self.coordinator.client.readback("connection_type")
