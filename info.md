# iRoom iTop / iDock

Local Home Assistant integration for **iRoom iTop / iDock Q6** docking stations
(now Eltako Austria), controlled over the LAN protocol (TCP, port 13601) — no
cloud, no app, no firmware change.

## Features
- Relay, LEDs, dock cover, audio/volume, iPad display on/off
- Digital inputs, buttons (events), battery/power/IR sensors
- Network configuration (DHCP / static, IP, mask, DNS, gateway, hostname, port)
- Automatic discovery (DHCP + active network search) and manual IP entry
- Local push (persistent TCP connection)

## Setup
Add via **Settings → Devices & Services → Add Integration → "iRoom iTop"**,
then either let it search the network or enter the dock's IP (default port 13601).
