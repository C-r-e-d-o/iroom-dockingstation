# iRoom iTop / iDock – Home Assistant integration

Local Home Assistant integration for **iRoom iTop / iDock Q6** docking stations.
It talks to the dock over its LAN protocol (TCP, port **13601**) — **no cloud, no
app, no firmware change**. The dock shows up as a single device with all its
entities.

Compatible products:

All products listed below with a serial number beginning with 0103:

- iBezel
- iTop
- iTopOnWall
- touchDock

> Independent community project. Not an official product and not affiliated with
> the device manufacturer. Use at your own risk.

> **Hardware-verified on:** model `iDock_Q6_TouchDock_Mode`, firmware 1.7.06. The
> other listed variants use the same LAN protocol but have not been individually
> verified on hardware. Writes that have not been verified are exposed read-only
> (see *Notes* and [PROTOCOL.md](PROTOCOL.md)).

## Features
- **Switches:** relay, iPad audio output
- **Lights:** LED Home + LED 1–6
- **Cover/Lock :** dock open/close
- **iPad display:** On/Off
- **Media player:** volume (absolute + up/down/mute), play/pause/next/prev
- **Binary sensors:** digital inputs 0–8, iPad docked, network status
- **Sensors:** battery, charge/supply current & voltage, IR level, firmware info,
  serial number; plus **read-only** diagnostics for the dock's installer/timing
  parameters (motor jam factor, settings delay, auto-open/close behaviour, IR
  sensitivity and timers, …) that are not yet verified on hardware
- **Buttons:** beep, toggle dock, iPad display on/off, save settings, reboot
- **Numbers / text / select:** display brightness, network settings
  (DHCP / static IP, IP, mask, DNS, gateway, hostname, port)
- **Events:** buttons 0–6, IR event
- **Services:** `get_unlock_pin` — returns the unlock PIN in the action response
  (admin only; not stored as a state or in history)
- **Discovery:** automatic (DHCP + active network scan) and manual IP entry
- **Local push** over a persistent TCP connection

## Installation

### Via HACS (custom repository)
1. HACS → ⋮ (top right) → **Custom repositories**.
2. Repository: `https://github.com/C-r-e-d-o/iroom-dockingstation`, category:
   **Integration** → **Add**.
3. Search for **iRoom iTop**, **Download**, then **restart Home Assistant**.

### Manual
Copy `custom_components/iroom_itop/` into your Home Assistant `config/custom_components/`
folder and restart.

## Setup
**Settings → Devices & Services → Add Integration → "iRoom iTop"**, then either
let it **search the network** or **enter the dock's IP** (default port 13601).
Tip: give the dock a fixed IP (DHCP reservation) so the address stays stable.

## Notes
- Some values are read-only over LAN by design (e.g. the access code is not
  retrievable; the serial number is display-only). The unlock PIN is **not**
  exposed as an entity — read it with the admin-only **`get_unlock_pin`** action
  (Developer Tools → Actions).
- **Installer- and motor-level parameters** (e.g. jam factor, settings delay,
  default-restore on start, demo mode, auto-open/close behaviour, IR sensitivity
  and the various timers) are exposed **read-only** until their write behaviour is
  verified on real hardware, because the dock auto-saves changes and a wrong value
  would stick. Only reversible operational controls (relay, LEDs, display
  brightness, volume, beep, dock open/close, iPad audio) and the verified network
  settings are writable. See [PROTOCOL.md](PROTOCOL.md) for the validation status.
- Changing IP, network mode or port can drop the connection — re-add the
  integration with the new address afterwards.
- The dock auto-saves changed settings a few seconds after a change (firmware
  behaviour); the **Save settings** button saves immediately.

## License
MIT — see [LICENSE](LICENSE).
