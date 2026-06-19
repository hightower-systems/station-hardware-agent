# Station Hardware Agent

[![CI](https://github.com/hightower-systems/station-hardware-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/hightower-systems/station-hardware-agent/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

A small local HTTP agent that bridges a browser or cloud web app to the
USB hardware on a retail / warehouse station:

- **ESC/POS receipt printer + cash drawer** (raw USB)
- **USB HID shipping scale** (Mettler-Toledo / DYMO / OEM postal scales)
- **Zebra ZPL label printer** (Windows print share)

It runs on the station's Windows machine, listens on `127.0.0.1`, and the
web app's browser tab calls it over loopback. Extracted and generalized
from agents running daily in production stores.

## Why this exists

A web app served over HTTPS can't talk to a USB printer or scale -- the
browser sandboxes pages away from local hardware. The fix is a local
agent that owns the devices and exposes them on `http://127.0.0.1`, which
the page calls from the user's browser. This is that agent, with a
pluggable driver per device and an honest security model.

## Devices

| Driver | Device | Transport | Key routes |
|---|---|---|---|
| `escpos_usb` | ESC/POS receipt printer + cash drawer | raw USB (python-escpos / libusb) | `POST /print`, `POST /open-drawer` |
| `hid_scale` | USB HID shipping scale | raw USB HID (hidapi) | `GET /scale` |
| `zebra_zpl` | Zebra ZPL label printer | Windows print share (UNC) | `POST /label`, `POST /label/bin-sticker` |

Enable the ones you need via `ENABLED_DRIVERS`. See [docs/devices.md](docs/devices.md).

## How it works

```
  Web app (https://your-app)         The station machine
  ----------------------------       ------------------------------------
  browser tab  ──fetch http://127.0.0.1:8765/...──►  Station Hardware Agent
                                                         ├─ escpos_usb  → receipt printer + drawer
                                                         ├─ hid_scale   → USB HID scale
                                                         └─ zebra_zpl   → Zebra label printer
```

Details in [docs/architecture.md](docs/architecture.md).

## Quick start

### Windows (autostart, recommended)

1. Install Python 3.11+ from python.org (tick **Add Python to PATH**).
2. Copy this folder to the station, e.g. `C:\station-hardware-agent\`.
3. Right-click `installers\install.bat` -> **Run as administrator**. It
   creates a venv, installs the agent, copies `.env.example` to `.env`,
   and registers a Task Scheduler entry that starts on every logon.
4. Edit `.env` and set `ALLOWED_ORIGIN` (and the device ids you use).
5. Start now without signing out:
   `schtasks /Run /TN "Station Hardware Agent"`.

For a manual run instead, double-click `installers\start_agent.bat`.

### Any platform (dev)

```bash
pip install -e ".[dev]"
cp .env.example .env        # then edit ALLOWED_ORIGIN
python -m hwbridge          # or: uvicorn hwbridge.app:app
```

## ⚠ Browser setup is required

Chrome and Edge now block public-origin pages from reaching `127.0.0.1`
unless Local Network Access is allowed for your site. **If you skip this,
a perfectly working agent will look broken.** Pick the tier that fits
(flag, permission prompt, or the `LocalNetworkAccessAllowedForUrls`
enterprise policy) in [docs/browser-setup.md](docs/browser-setup.md).

## Configuration

All config is environment / `.env` (see [.env.example](.env.example)).
The only required value is `ALLOWED_ORIGIN`. Per-device keys are in
[docs/devices.md](docs/devices.md).

## HTTP API

| Method | Path | Driver | Body / result |
|---|---|---|---|
| `GET` | `/status` | core | agent + per-driver liveness |
| `POST` | `/print` | escpos_usb | `{format:"text", content, cut, open_drawer_after}` |
| `POST` | `/open-drawer` | escpos_usb | (none) |
| `POST` | `/test-print` | escpos_usb | prints a diagnostic slip |
| `GET` | `/scale` | hid_scale | `{status, weight, unit:"lbs", stable}` |
| `POST` | `/label` | zebra_zpl | raw ZPL bytes |
| `POST` | `/label/bin-sticker` | zebra_zpl | `{sku, upc?}` |
| `POST` | `/label/item-barcode` | zebra_zpl | `{upc, quantity}` |

The receipt printer prints **ESC/POS text** (not bitmaps); `/print` only
accepts `format:"text"`.

## Security model

- **Loopback only** -- binds `127.0.0.1`, unreachable off the machine.
- **Origin pin** -- every request must carry `Origin: <ALLOWED_ORIGIN>`
  or it's rejected `403`. No token (it would live in the browser anyway);
  loopback + origin pin is the real boundary.

## Development

```bash
pip install -e ".[dev]"
pytest
```

Tests use fakes for every device, so no hardware (and no libusb/hidapi
backend) is needed to run them.

## Project layout

```
hwbridge/
  app.py            FastAPI factory + middleware + /status
  config.py         settings (env / .env)
  middleware.py     Private Network Access header (outermost)
  tray.py           optional system-tray status icon
  __main__.py       python -m hwbridge entrypoint
  drivers/          one module per device + the registry
  labels/zpl.py     ZPL label builders
docs/               architecture, devices, browser setup
installers/         Windows install.bat / start_agent.bat
tests/              hardware-free unit + app tests
```

## Status & platform

Beta. Targeted at **Windows** stations (Task Scheduler autostart, cash
drawer, Zebra print share). The USB-HID and ESC/POS layers are
cross-platform; the deployment story is Windows.

## License

[Apache 2.0](LICENSE). Extracted and generalized from production retail
and warehouse station agents.
