"""Konstanten & Protokoll-Abbildung der iRoom-iTop-Integration.

Protokoll (LAN, TCP, Standardport 13601):  typ:name:wert;
  typ = cmd (setzen) | req (abfragen) | inf (Antwort) | evn (Event)
Klartext, nicht case-sensitiv, max. 255 Zeichen je Befehl, ';' als Trenner.
(Am echten Gerät bestätigt über das bestehende itop-web.)
"""
from __future__ import annotations

DOMAIN = "iroom_itop"
DEFAULT_PORT = 13601
DEFAULT_NAME = "iRoom iTop"
MANUFACTURER = "iRoom"
MODEL = "iDock Q6"

# Signale (dispatcher)
SIGNAL_UPDATE = f"{DOMAIN}_update"      # Zustand aktualisiert
SIGNAL_EVENT = f"{DOMAIN}_event"        # evn:<name>:<value> (Tasten, IR)

# Zeitverhalten
KEEPALIVE_S = 120          # Protokoll verlangt <=150 s
RECONNECT_MIN_S = 2
RECONNECT_MAX_S = 30

# ---- Hardware-Eckdaten (Firmware v1.7.06 bestätigt) ----
LED_COUNT = 7    # led0 = Home, led1..6 = Touch-Tasten (über iBezel)
BTN_COUNT = 7    # button0 = Home, button1..6
DI_COUNT = 9     # digital0..8

# ---- Befehle mit Aufzählungswerten ----
ENUMS = {
    "idock": ["open", "close", "toggle"],
    "relay0": ["open", "close", "toggle"],   # im iTop-Modus wirkungslos (laut App)
    "volume": ["up", "down", "mute", "unmute", "mute_toggle"],
    "music": ["play", "pause", "next", "prev", "playpause"],
    "ipad": ["wakeup", "sleep", "charge", "drain"],
}
# ---- Befehle mit Zahlenbereich ----
# volume kann zusätzlich absolut (0..100) gesetzt werden -> im media_player direkt.
RANGES = {
    "beep": (1, 100),
    **{f"led{i}": (0, 100) for i in range(LED_COUNT)},
}
VOLUME_RANGE = (0, 100)   # absolute Lautstärke via cmd:volume:<n>;

# ---- Abfragen (req) ----
REQUESTS = {
    "infupdate": "standard",
    "alive": "1",
    "dock_fw": "1",
    "boot_fw": "1",
    "bezel_fw": "1",
    "model": None,
    "unsaved_changes": "1",
    "reboot": None,
}

# ---- Konfigurationsparameter (lesbar via req:<name>:1;, setzbar via cmd) ----
# Typen: bool | uint:<max> | percent | ip | port | pin | text:<maxlen>
PARAMS = {
    # Netzwerk (Namen aus App bestätigt: ip/subnet_mask/router/dns/port/host_name)
    "host_name": "text:32",
    "connection_type": "uint:10",
    "ip": "ip",
    "subnet_mask": "ip",
    "router": "ip",
    "dns": "ip",
    "port": "port",
    # Sicherheit
    "accesscode": "text:32",          # nur schreibbar
    "pin": "pin",
    "default_accesscode": "text:32",
    "serial_nr": "text:32",           # Schreiben nur über App-Kanal erlaubt (LAN ignoriert es evtl.)
    # Allgemein
    "unlock_time": "uint:65535",
    "keyboard_function": "bool",
    "ibezel_function": "bool",
    "automatic_switch_back_to_ibezel": "bool",
    "switch_back_time": "uint:65535",
    "direct_control": "bool",
    "ibezel_beep": "bool",
    # Dock
    "brightness": "percent",
    "enable_audio_output": "bool",
    "open_without_ipad": "bool",
    "open_at_power_on": "bool",
    "open_at_power_off": "bool",
    "close_automatically": "bool",
    "close_time": "uint:65535",
    "relay_ext": "bool",
    "external_contact": "bool",
    "release_demo_mode": "bool",
    "demo_cycles_per_hour": "uint:1000",
    # IR / Panel
    "sensitivity": "uint:255",
    "wake_up_ipad_on_wink": "bool",
    "auto_hide_panel_button": "bool",
    "auto_hide_panel_button_time": "uint:65535",
    "glow_time": "uint:255",
    "reglow_time": "uint:255",
    # System / Staged-Commit
    "always_docked": "bool",
    "set_default_par_on_start": "bool",
    "jam_factor": "uint:65535",
    "settings_delay": "uint:65535",
    "save_changes": "uint:1",         # Aktion (Staged-Commit speichern)
}

CONFIG_READABLE = [p for p in PARAMS if p not in ("accesscode", "save_changes")]
INFO_READABLE = [
    "model", "api", "mac", "serial_nr", "op_ho", "is_accesscode_valid",
    "network_connected", "network_established", "battery_level", "battery_state",
    "dockingstate", "volume", "relay0", "unsaved_changes",
    "supply", "supply_ipad", "charge_current", "available_current", "irlevel",
]

# Bereiche/Einheiten für Konfig-Parameter, die als number-Entität erscheinen
PARAM_NUMBER_META = {
    "unlock_time": ("s", 0, 65535),
    "switch_back_time": ("s", 0, 65535),
    "close_time": ("s", 0, 65535),
    "auto_hide_panel_button_time": ("s", 0, 65535),
    "sensitivity": (None, 0, 255),
    "brightness": ("%", 0, 100),
    "jam_factor": (None, 0, 65535),
    "settings_delay": ("s", 0, 65535),
}
PARAM_BOOL = [p for p, t in PARAMS.items() if t == "bool"]
