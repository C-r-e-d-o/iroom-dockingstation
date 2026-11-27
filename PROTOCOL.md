# iRoom iDock – LAN/TCP-Steuerprotokoll (Port 13601)

Rekonstruiert aus Firmware (v1.7.06) **und** App-Quellcode (`iBezel/`), gegen
Simulator verifiziert. Grundlage der HA-Integration.

## Hardware-Validierung

Nicht alle Befehle sind gleich stark abgesichert. Die Integration gibt deshalb
nur Schreibzugriffe als beschreibbare Entitäten frei, die an echter Hardware
geprüft wurden oder von Natur aus reversibel sind; alles andere ist read-only.

Referenzgerät: **`iDock_Q6_TouchDock_Mode`, Firmware 1.7.06**.

| Klasse | Validierung | In HA |
|---|---|---|
| Netzwerk-Modus `connection_type` (DHCP=`1`, Static=`0`) | an Hardware gelesen in DHCP- **und** Static-Modus | **beschreibbar** (select) |
| Netzwerk-Adressfelder `ip`/`subnet_mask`/`dns`/`router`/`host_name`/`port` | an Hardware gelesen/gesetzt | **beschreibbar** (text) |
| Bedien-Controls `relay0`, `led0..6`, `beep`, `volume`, `idock`/`ipad`/`music`, Display-`brightness`, `enable_audio_output` | reversibel, kein Staged-Commit-Risiko | **beschreibbar** |
| Installer-/Motor-/Timing-Parameter `jam_factor`, `settings_delay`, `set_default_par_on_start`, `release_demo_mode`, `always_docked`, `close_time`, `unlock_time`, `switch_back_time`, `sensitivity`, Auto-Open/Close-Booleans, Panel-/IR-Parameter … | nur aus Firmware/App rekonstruiert, **nicht** an Hardware verifiziert | **read-only** (Diagnose-Sensor) |

Hintergrund: Der Dock speichert geänderte Parameter per Staged-Commit nach
wenigen Sekunden selbst ab (`settings_delay`), d. h. ein falsch gewählter Wert
bliebe persistent hängen und könnte den Dock bis zu einem Reset vor Ort
verstellen. Bis die betroffenen Schreibpfade an echter Hardware bestätigt sind
(Modell, Firmware, beobachtete Wirkung), bleiben sie read-only.

## Transport
- TCP, Standardport **13601**, reiner **UTF-8-Text**, **kein** Preamble/Länge/
  Checksumme, **kein Login**.
- Format je Befehl: `typ:name[:wert];`  — Trenner `:`, Terminator `;`.
- `typ` = `cmd` (setzen) · `req` (abfragen) · `inf` (Antwort/Status) · `evn` (Event).
- Mehrere Befehle hintereinander erlaubt (`a;b;`). Empfang: Stream puffern, auf
  `;` splitten (TCP fragmentiert beliebig).
- Nach Connect zuerst `req:model;` senden (sonst viele Funktionen gesperrt),
  dann Status abfragen. Verbindung mit periodischem `req:alive;` halten (<150 s).
- Groß/Kleinschreibung: Config-Keys `klein_mit_unterstrich`, Automations-Keys
  `CamelCase`. Bool = `0`/`1`.

> Die binäre `55AA`-Variante (VTTCPHandler in der App) ist der **Legacy/IO83-
> bzw. Kabel-Pfad** und gilt NICHT für 13601. Nur Klartext verwenden.

## Direktbefehle
| name | Werte |
|---|---|
| `idock` | open, close, toggle |
| `relay0` | open, close, toggle (im iTop-Modus wirkungslos) |
| `volume` | up, down, mute, unmute, mute_toggle · **oder absolut** `cmd:volume:<0..100>;` |
| `music` | play, pause, playpause, next, prev |
| `ipad` | wakeup, sleep, charge, drain |
| `beep` | 1..100 (Dauer) |
| `led0..led6` | 0..100 (Helligkeit) |

## Konfig-Parameter (setzen `cmd:<name>:<wert>;`, lesen `req:<name>;`)
Netzwerk: `host_name`, `connection_type`, `ip`, `subnet_mask`, `router`, `dns`,
`port`, `network_connected`(ro), `network_established`(ro).
Sicherheit: `accesscode`(wo), `pin`(wo), `default_accesscode`,
`is_accesscode_valid` (Check via `cmd:is_accesscode_valid:<code>;` → `inf:…:0|1;`).
Allgemein: `keyboard_function`, `ibezel_function`, `switch_back_time`,
`unlock_time`, `automatic_switch_back_to_ibezel`, `direct_control`, `ibezel_beep`.
Dock: `brightness`, `enable_audio_output`, `open_without_ipad`, `open_at_power_on`,
`open_at_power_off`, `close_automatically`, `close_time`, `relay_ext`,
`external_contact`, `release_demo_mode`, `demo_cycles_per_hour`.
IR/Panel: `sensitivity`, `wake_up_ipad_on_wink`, `auto_hide_panel_button`,
`auto_hide_panel_button_time`, `glow_time`, `reglow_time`.
System/Status: `always_docked`, `set_default_par_on_start`, `jam_factor`,
`settings_delay`, `save_changes` (Aktion: Staged-Commit speichern).
Nur lesbar: `model`, `api`, `serial_nr`, `op_ho`, `mac`, `supply`, `supply_ipad`,
`charge_current`, `available_current`, `battery_level`, `battery_state`,
`dockingstate`, `digital0..8`, `button0..6`, `irevent`, `ir_raw`, `irlevel`,
`dock_fw`, `boot_fw`, `bezel_fw`. Neustart: `req:reboot;`.

> Welche dieser setzbaren Parameter die Integration tatsächlich beschreibbar
> macht, richtet sich nach der Tabelle unter *Hardware-Validierung*; ungeprüfte
> Parameter werden read-only angezeigt.

## Antworten / Events
- Antworten/Status als `inf:<name>:<wert>;`. Unaufgeforderte Änderungen (Taste,
  Docking, Strom …) kommen ebenfalls als `inf:`/`evn:` desselben Schemas.
- Modell-Strings: `iDock_Q6`, `iDock_Q6_Q5_Mode`, `iDock_Q6_ITOP_Mode`,
  `iDock_Q6_ITOPLock_Mode`, `iDock_Q6_TouchDock_Mode`, `iDock_Q6_SPM_Mode`.

## Automations-Engine (noch nicht als HA-Dienste umgesetzt)
Hierarchie Device → Command → ActionTable → Action → ButtonConfiguration /
ButtonDefinition. Anlegen über `cmd:Add…:<:-getrennte Felder>;`, IDs vorher per
`req:newDeviceID;` / `req:newCommandID;` / `req:newActionTableID;` holen und auf
`inf:new…ID:<n>;` warten. Lesen `req:All…;` / `req:…ByID:<id>;`, löschen
`cmd:Remove…;`. Feldreihenfolgen siehe App-Quellen (DeviceData/CommandData/
ActionData/ActionTableData/ButtonConfigurationData/ButtonNameData).
