"""Config-Flow: automatische Suche (Scan + DHCP) und manuelle IP-Eingabe."""
from __future__ import annotations

import asyncio
import socket
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant

from .const import DEFAULT_NAME, DEFAULT_PORT, DOMAIN

try:  # Lage von DhcpServiceInfo variiert je nach HA-Version
    from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo
except ImportError:  # ältere HA
    from homeassistant.components.dhcp import DhcpServiceInfo  # type: ignore


async def _protocol_probe(host: str, port: int = DEFAULT_PORT) -> str | None:
    """Verbindet und prüft, ob das Gerät im iDock-Protokoll antwortet.
    Rückgabe: Modellname (oder 'iDock') bei Antwort, sonst None."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=0.8
        )
    except Exception:  # noqa: BLE001
        return None
    try:
        writer.write(b"req:model;req:infupdate:standard;")
        await writer.drain()
        data = b""
        try:
            data = await asyncio.wait_for(reader.read(512), timeout=1.5)
        except asyncio.TimeoutError:
            pass
        if data and b"inf:" in data:
            text = data.decode("ascii", "replace")
            for part in text.split(";"):
                if part.startswith("inf:model:"):
                    return part.split(":", 2)[2] or "iDock"
            return "iDock"
        return None
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:  # noqa: BLE001
            pass


async def _tcp_open(host: str, port: int) -> bool:
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=4
        )
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:  # noqa: BLE001
            pass
        return True
    except Exception:  # noqa: BLE001
        return False


def _local_bases() -> list[str]:
    """Ermittelt die /24-Basis(en) der lokalen Netze (best effort)."""
    bases: list[str] = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        bases.append(ip.rsplit(".", 1)[0])
    except Exception:  # noqa: BLE001
        pass
    return bases


async def _scan(hass: HomeAssistant) -> dict[str, str]:
    """Scannt die lokalen /24-Netze nach protokollfähigen iRoom-Docks."""
    bases = await hass.async_add_executor_job(_local_bases)
    found: dict[str, str] = {}
    sem = asyncio.Semaphore(60)

    async def one(ip: str) -> None:
        async with sem:
            model = await _protocol_probe(ip)
            if model:
                found[ip] = model

    tasks = [one(f"{base}.{i}") for base in bases for i in range(1, 255)]
    if tasks:
        await asyncio.gather(*tasks)
    return found


class ItopConfigFlow(ConfigFlow, domain=DOMAIN):
    """Einrichtung über automatische Suche oder manuelle IP."""

    VERSION = 1

    def __init__(self) -> None:
        self._found: dict[str, str] = {}
        self._dhcp_host: str | None = None

    # --- Einstieg: Menü ------------------------------------------------
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return self.async_show_menu(step_id="user", menu_options=["search", "manual"])

    # --- Automatische Suche (aktiver Scan) -----------------------------
    async def async_step_search(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            host = user_input[CONF_HOST]
            await self.async_set_unique_id(f"{host}:{DEFAULT_PORT}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"{DEFAULT_NAME} ({host})",
                data={CONF_HOST: host, CONF_PORT: DEFAULT_PORT},
            )

        self._found = await _scan(self.hass)
        configured = {e.data.get(CONF_HOST) for e in self._async_current_entries()}
        choices = {ip: f"{ip} – {m}" for ip, m in self._found.items() if ip not in configured}
        if not choices:
            # nichts gefunden -> direkt zur manuellen Eingabe
            return await self.async_step_manual()
        schema = vol.Schema({vol.Required(CONF_HOST): vol.In(choices)})
        return self.async_show_form(step_id="search", data_schema=schema)

    # --- Manuelle IP ---------------------------------------------------
    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = int(user_input[CONF_PORT])
            await self.async_set_unique_id(f"{host}:{port}")
            self._abort_if_unique_id_configured()
            if await _protocol_probe(host, port) is not None or await _tcp_open(host, port):
                return self.async_create_entry(
                    title=f"{DEFAULT_NAME} ({host})",
                    data={CONF_HOST: host, CONF_PORT: port},
                )
            errors["base"] = "cannot_connect"
        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=""): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
            }
        )
        return self.async_show_form(step_id="manual", data_schema=schema, errors=errors)

    # --- Automatische DHCP-Erkennung -----------------------------------
    async def async_step_dhcp(self, discovery_info: DhcpServiceInfo) -> ConfigFlowResult:
        host = discovery_info.ip
        await self.async_set_unique_id(f"{host}:{DEFAULT_PORT}")
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})
        self._dhcp_host = host
        self.context["title_placeholders"] = {"name": f"{DEFAULT_NAME} ({host})"}
        return await self.async_step_dhcp_confirm()

    async def async_step_dhcp_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        assert self._dhcp_host
        host = self._dhcp_host
        if user_input is not None:
            return self.async_create_entry(
                title=f"{DEFAULT_NAME} ({host})",
                data={CONF_HOST: host, CONF_PORT: DEFAULT_PORT},
            )
        return self.async_show_form(
            step_id="dhcp_confirm", description_placeholders={"host": host}
        )
