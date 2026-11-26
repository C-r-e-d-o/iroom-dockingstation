"""Services for the iRoom iTop integration.

Exposes an admin-only action that returns the dock's unlock PIN in the action
response. The PIN is therefore never published as an entity state or stored in
the recorder history database.
"""
from __future__ import annotations

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import async_register_admin_service

from .const import DOMAIN
from .coordinator import ItopCoordinator

SERVICE_GET_UNLOCK_PIN = "get_unlock_pin"
ATTR_CONFIG_ENTRY_ID = "config_entry_id"

_SCHEMA = vol.Schema({vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string})


def _resolve(hass: HomeAssistant, call: ServiceCall) -> ItopCoordinator:
    """Pick the target coordinator, requiring an id only when ambiguous."""
    entries: dict[str, ItopCoordinator] = hass.data.get(DOMAIN, {})
    if not entries:
        raise ServiceValidationError("The iRoom iTop integration is not set up.")
    entry_id = call.data.get(ATTR_CONFIG_ENTRY_ID)
    if entry_id is not None:
        coord = entries.get(entry_id)
        if coord is None:
            raise ServiceValidationError(f"Unknown config entry id: {entry_id}")
        return coord
    if len(entries) == 1:
        return next(iter(entries.values()))
    raise ServiceValidationError(
        "More than one iRoom iTop device is configured; "
        "pass 'config_entry_id' to choose one."
    )


def async_setup_services(hass: HomeAssistant) -> None:
    """Register integration services once."""
    if hass.services.has_service(DOMAIN, SERVICE_GET_UNLOCK_PIN):
        return

    async def _get_unlock_pin(call: ServiceCall) -> dict:
        coord = _resolve(hass, call)
        return {"pin": coord.inf("pin")}

    # admin-only + response-only: value is returned to the caller, never stored.
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_GET_UNLOCK_PIN,
        _get_unlock_pin,
        schema=_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


def async_unload_services(hass: HomeAssistant) -> None:
    """Remove integration services when the last entry is unloaded."""
    hass.services.async_remove(DOMAIN, SERVICE_GET_UNLOCK_PIN)
