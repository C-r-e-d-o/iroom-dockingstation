"""Asynchroner TCP-Client für die iRoom-iTop (LAN-Klartextprotokoll).

Portierung der erprobten itop-web-Logik auf asyncio für Home Assistant.
Hält den aktuellen Zustand (inf/evn) und meldet Änderungen per Callback.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from collections.abc import Callable

from .const import (
    ENUMS, RANGES, PARAMS, REQUESTS, CONFIG_READABLE, INFO_READABLE,
    KEEPALIVE_S, RECONNECT_MIN_S, RECONNECT_MAX_S,
)

_LOGGER = logging.getLogger(__name__)
RAW_RE = re.compile(r"^[a-z0-9_]+(:[a-z0-9_.\-]+)*;$")


# ---------------------------------------------------------------- Validierung
def _validate_param(name: str, value, spec: str) -> str:
    v = str(value).strip()
    kind, _, arg = spec.partition(":")
    if kind == "bool":
        low = v.lower()
        if low in ("1", "true", "on", "yes"):
            return "1"
        if low in ("0", "false", "off", "no"):
            return "0"
        raise ValueError(f"{name}: 0/1 erwartet")
    if kind in ("uint", "percent", "port"):
        lo, hi = (0, 100) if kind == "percent" else (1, 65535) if kind == "port" else (0, int(arg))
        try:
            n = int(float(v))
        except ValueError:
            raise ValueError(f"{name}: Zahl erwartet")
        if not lo <= n <= hi:
            raise ValueError(f"{name}: {n} außerhalb {lo}…{hi}")
        return str(n)
    if kind == "ip":
        parts = v.split(".")
        if len(parts) != 4 or not all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
            raise ValueError(f"{name}: IPv4 erwartet")
        return ".".join(str(int(p)) for p in parts)
    if kind == "pin":
        if not (v.isdigit() and len(v) == 4):
            raise ValueError(f"{name}: 4-stellige PIN erwartet")
        return v
    if kind == "text":
        maxlen = int(arg) if arg else 64
        if not v or len(v) > maxlen or ":" in v or ";" in v:
            raise ValueError(f"{name}: 1…{maxlen} Zeichen, ohne ':' ';'")
        if not re.match(r"^[\x20-\x7e]+$", v):
            raise ValueError(f"{name}: nur ASCII")
        return v
    raise ValueError(f"{name}: unbekannter Typ {kind}")


def build_cmd(cmd: str, value) -> str:
    cmd = str(cmd).strip().lower()
    if cmd in ENUMS:
        value = str(value).strip().lower()
        if value not in ENUMS[cmd]:
            raise ValueError(f"Ungültiger Wert für {cmd}: {value}")
    elif cmd in RANGES:
        lo, hi = RANGES[cmd]
        v = int(float(str(value).strip()))
        if not lo <= v <= hi:
            raise ValueError(f"{cmd}: {v} außerhalb {lo}…{hi}")
        value = str(v)
    elif cmd in PARAMS:
        value = _validate_param(cmd, value, PARAMS[cmd])
    else:
        raise ValueError(f"Unbekannter Befehl: {cmd}")
    return f"cmd:{cmd}:{value};"


def build_req(req: str) -> str:
    req = str(req).strip().lower()
    if req in REQUESTS:
        p = REQUESTS[req]
        return f"req:{req}:{p};" if p else f"req:{req};"
    return f"req:{req}:1;"   # beliebigen lesbaren Namen abfragen


class ItopClient:
    """Verwaltet die TCP-Verbindung, hält Zustand, meldet Änderungen."""

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._task: asyncio.Task | None = None
        self._ka_task: asyncio.Task | None = None
        self._wlock = asyncio.Lock()
        self._stop = False
        self._reconnect = asyncio.Event()
        self.connected = False
        self.last_rx = 0.0
        # Zustand: {"inf": {...}, "evn": {...}}
        self.state: dict[str, dict[str, str]] = {"inf": {}, "evn": {}}
        self.on_update: Callable[[], None] | None = None
        self.on_event: Callable[[str, str], None] | None = None

    # --- Lebenszyklus ---------------------------------------------------
    def start(self) -> None:
        self._stop = False
        self._task = asyncio.create_task(self._run())
        self._ka_task = asyncio.create_task(self._keepalive())

    async def stop(self) -> None:
        self._stop = True
        self._reconnect.set()
        for t in (self._task, self._ka_task):
            if t:
                t.cancel()
        await self._close_writer()

    async def _close_writer(self) -> None:
        async with self._wlock:
            if self._writer:
                try:
                    self._writer.close()
                    await asyncio.wait_for(self._writer.wait_closed(), timeout=2)
                except Exception:  # noqa: BLE001
                    pass
            self._writer = None
            self._reader = None

    # --- Senden ---------------------------------------------------------
    async def send_raw(self, line: str) -> None:
        if not line.endswith(";"):
            line += ";"
        async with self._wlock:
            if not self._writer:
                raise ConnectionError("Keine Verbindung zur iTop")
            self._writer.write(line.encode("ascii"))
            await self._writer.drain()

    async def cmd(self, name: str, value) -> None:
        await self.send_raw(build_cmd(name, value))

    async def req(self, name: str) -> None:
        await self.send_raw(build_req(name))

    async def readback(self, name: str) -> None:
        """Nach cmd den Wert aktiv nachfragen (Gerät sendet kein inf von selbst)."""
        await asyncio.sleep(0.25)
        for q in (name, "unsaved_changes"):
            try:
                await self.send_raw(f"req:{q}:1;")
            except Exception:  # noqa: BLE001
                return
            await asyncio.sleep(0.1)

    async def refresh_all(self) -> None:
        names = list(dict.fromkeys(CONFIG_READABLE + INFO_READABLE))
        for name in names:
            try:
                await self.send_raw(f"req:{name}:1;")
            except Exception:  # noqa: BLE001
                return
            await asyncio.sleep(0.05)

    def request_reconnect(self) -> None:
        self._reconnect.set()

    # --- Verbindungsschleife -------------------------------------------
    async def _run(self) -> None:
        backoff = RECONNECT_MIN_S
        while not self._stop:
            try:
                self._reader, self._writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, self.port), timeout=8
                )
                self.connected = True
                self._notify()
                backoff = RECONNECT_MIN_S
                _LOGGER.info("iTop verbunden: %s:%s", self.host, self.port)
                # Modell zuerst – ohne Modell bleiben viele Funktionen gesperrt (lt. App)
                for line in ("req:model;", "req:infupdate:standard;", "req:dock_fw:1;",
                             "req:boot_fw:1;", "req:bezel_fw:1;"):
                    await self.send_raw(line)
                    await asyncio.sleep(0.1)
                asyncio.create_task(self.refresh_all())
                await self._read_loop()
            except asyncio.CancelledError:
                break
            except Exception as e:  # noqa: BLE001
                _LOGGER.debug("iTop Verbindungsfehler: %s", e)
            finally:
                if self.connected:
                    self.connected = False
                    self._notify()
                await self._close_writer()
            if self._stop:
                break
            try:
                await asyncio.wait_for(self._reconnect.wait(), timeout=backoff)
            except asyncio.TimeoutError:
                pass
            self._reconnect.clear()
            backoff = min(backoff * 2, RECONNECT_MAX_S)

    async def _read_loop(self) -> None:
        buf = ""
        assert self._reader
        while not self._stop:
            data = await self._reader.read(1024)
            if not data:
                raise ConnectionError("Verbindung geschlossen")
            buf += data.decode("ascii", errors="replace")
            while ";" in buf:
                msg, buf = buf.split(";", 1)
                msg = msg.strip()
                if msg:
                    self._handle(msg)
            if len(buf) > 2048:
                buf = ""

    def _handle(self, msg: str) -> None:
        self.last_rx = time.time()
        parts = msg.split(":")
        if len(parts) < 2:
            return
        typ, name = parts[0].lower(), parts[1].lower()
        value = ":".join(parts[2:]) if len(parts) > 2 else ""
        if typ in ("inf", "evn"):
            self.state[typ][name] = value
            if typ == "evn" and self.on_event:
                self.on_event(name, value)
            self._notify()

    def _notify(self) -> None:
        if self.on_update:
            self.on_update()

    async def _keepalive(self) -> None:
        try:
            while not self._stop:
                await asyncio.sleep(KEEPALIVE_S)
                if not self.connected:
                    continue
                sent = time.time()
                try:
                    await self.send_raw("req:alive:1;")
                except Exception:  # noqa: BLE001
                    continue
                await asyncio.sleep(20)
                if self.last_rx < sent:
                    _LOGGER.info("iTop: keine alive-Antwort – reconnect")
                    self.request_reconnect()
        except asyncio.CancelledError:
            pass
