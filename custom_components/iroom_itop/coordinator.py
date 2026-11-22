"""DataUpdateCoordinator-Wrapper um den iTop-Client (Push-Modell)."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, SIGNAL_EVENT
from .itop_client import ItopClient

_LOGGER = logging.getLogger(__name__)


class ItopCoordinator(DataUpdateCoordinator[dict]):
    """Hält den Client; verteilt dessen Push-Updates an die Entitäten."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, host: str, port: int) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, config_entry=entry)  # kein update_interval -> rein Push
        self.entry_id = entry.entry_id
        self.client = ItopClient(host, port)
        self.client.on_update = self._on_update
        self.client.on_event = self._on_event

    @callback
    def _on_update(self) -> None:
        self.async_set_updated_data(self.client.state)

    @callback
    def _on_event(self, name: str, value: str) -> None:
        async_dispatcher_send(self.hass, f"{SIGNAL_EVENT}_{self.config_entry.entry_id}", name, value)

    async def async_start(self) -> None:
        self.client.start()
        # Anfangszustand setzen, damit Entitäten nicht ewig "unknown" sind
        self.async_set_updated_data(self.client.state)

    async def async_stop(self) -> None:
        await self.client.stop()

    # Komfort-Helfer für Entitäten
    def inf(self, name: str, default=None):
        return self.client.state["inf"].get(name, default)

    def evn(self, name: str, default=None):
        return self.client.state["evn"].get(name, default)

    @property
    def available(self) -> bool:
        return self.client.connected
