"""Sensoren: Batterie, Versorgung, Ströme, IR, Firmware-Infos.

Zusätzlich werden Konfig-/Installer-Parameter, die (noch) nicht an echter
Hardware verifiziert sind, hier read-only als Diagnose-Sensoren angezeigt
(READONLY_BOOL_PARAMS / READONLY_NUMBER_PARAMS, siehe const.py). So bleibt der
aktuelle Wert sichtbar, ohne dass ein ungeprüfter Schreibzugriff möglich ist.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable

from homeassistant.components.sensor import (
    SensorEntity, SensorDeviceClass, SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE, UnitOfElectricCurrent, UnitOfElectricPotential,
)
from homeassistant.core import HomeAssistant
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN, PARAM_NUMBER_META, READONLY_BOOL_PARAMS, READONLY_NUMBER_PARAMS,
)
from .coordinator import ItopCoordinator
from .entity import ItopEntity


@dataclass(frozen=True)
class ItopSensorDesc:
    key: str
    name: str
    unit: str | None = None
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None
    diagnostic: bool = False
    conv: Callable[[str], object] | None = None


def _mv(v: str):
    return int(float(v))


def _onoff(v: str):
    return {"1": "on", "0": "off", "true": "on", "false": "off"}.get(
        str(v).strip().lower(), v
    )


SENSORS = [
    ItopSensorDesc("battery_level", "Battery", PERCENTAGE, SensorDeviceClass.BATTERY,
                   SensorStateClass.MEASUREMENT, conv=_mv),
    ItopSensorDesc("battery_state", "Battery state"),
    ItopSensorDesc("charge_current", "Charge current", UnitOfElectricCurrent.MILLIAMPERE,
                   SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, conv=_mv),
    ItopSensorDesc("available_current", "Available current", UnitOfElectricCurrent.MILLIAMPERE,
                   SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, conv=_mv),
    ItopSensorDesc("supply", "Supply voltage", UnitOfElectricPotential.MILLIVOLT,
                   SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, conv=_mv),
    ItopSensorDesc("supply_ipad", "iPad supply", UnitOfElectricPotential.MILLIVOLT,
                   SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, conv=_mv),
    ItopSensorDesc("irlevel", "IR level", state_class=SensorStateClass.MEASUREMENT, conv=_mv),
    ItopSensorDesc("volume", "Volume", PERCENTAGE, conv=_mv),
    # Diagnostics / info
    ItopSensorDesc("model", "Model", diagnostic=True),
    ItopSensorDesc("mac", "MAC address", diagnostic=True),
    ItopSensorDesc("serial_nr", "Serial number (determines the MAC address)", diagnostic=True),
    ItopSensorDesc("dock_fw", "Firmware", diagnostic=True),
    ItopSensorDesc("boot_fw", "Bootloader", diagnostic=True),
    ItopSensorDesc("bezel_fw", "iBezel firmware", diagnostic=True),
    ItopSensorDesc("op_ho", "Operating hours", diagnostic=True),
]


def _readonly_param_sensors() -> list[ItopSensorDesc]:
    """Config/installer parameters shown read-only until verified on hardware."""
    out: list[ItopSensorDesc] = []
    for key in READONLY_BOOL_PARAMS:
        out.append(ItopSensorDesc(
            key, key.replace("_", " ").capitalize(), diagnostic=True, conv=_onoff))
    for key in READONLY_NUMBER_PARAMS:
        unit = PARAM_NUMBER_META[key][0]
        out.append(ItopSensorDesc(
            key, key.replace("_", " ").capitalize(), unit=unit,
            diagnostic=True, conv=_mv))
    return out


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            add: AddEntitiesCallback) -> None:
    coord: ItopCoordinator = hass.data[DOMAIN][entry.entry_id]
    add(ItopSensor(coord, entry.entry_id, d)
        for d in [*SENSORS, *_readonly_param_sensors()])


class ItopSensor(ItopEntity, SensorEntity):
    def __init__(self, coord, entry_id, desc: ItopSensorDesc):
        super().__init__(coord, entry_id, desc.key)
        self._d = desc
        self._attr_name = desc.name
        self._attr_native_unit_of_measurement = desc.unit
        self._attr_device_class = desc.device_class
        self._attr_state_class = desc.state_class
        if desc.diagnostic:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self):
        v = self.coordinator.inf(self._d.key)
        if v is None or v == "":
            return None
        if self._d.conv:
            try:
                return self._d.conv(v)
            except (ValueError, TypeError):
                return None
        return v
