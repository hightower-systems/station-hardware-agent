# Architecture

## The problem

A web app (served over HTTPS, often from the cloud) cannot talk to a USB
printer or scale plugged into the user's machine. Browsers sandbox web
pages away from local hardware. The standard fix is a small **local
agent**: a process on the same machine that owns the hardware and exposes
it over `http://127.0.0.1`, which the web page calls from the user's
browser.

```
  Web app (https://your-app)         The user's machine
  ----------------------------       ------------------------------------
  browser tab  ──fetch http://127.0.0.1:8765/...──►  Station Hardware Agent
                                                         │
                                                         ├─ escpos_usb  → USB receipt printer + drawer
                                                         ├─ hid_scale   → USB HID scale
                                                         └─ zebra_zpl   → Zebra label printer (print share)
```

## Security model

The agent can drive physical hardware, so access is locked down two ways,
both required:

1. **Loopback bind.** It listens on `127.0.0.1` only. Nothing off the
   machine can reach it.
2. **Origin pin.** Every non-preflight request must carry an `Origin`
   header equal to the configured `allowed_origin`, or it is rejected
   `403`. This stops a random site the user wanders onto from scripting
   the local hardware.

There is intentionally no auth token: a token would have to live in the
browser where any script on the allowed origin could read it anyway, so
it would add ceremony without adding protection. Loopback + origin pin is
the honest boundary.

## Browser gating: PNA and LNA

Modern Chrome/Edge restrict requests from a public origin to a local
address. The agent emits the legacy **Private Network Access** response
header (`Access-Control-Allow-Private-Network: true`) for the allowed
origin. The newer **Local Network Access** model moves the decision to a
client-side permission/flag/enterprise policy that the *operator* must
grant. This is the most common "the agent is running but the page can't
reach it" failure -- see [browser-setup.md](browser-setup.md).

### Middleware order matters

Middleware is registered CORS -> origin-check -> PNA, which makes the PNA
middleware **outermost**. On the response path it appends the PNA header
*last*, so the CORS layer cannot strip or overwrite it. (The original
Flask version of this agent hit exactly that bug: `flask-cors` re-emitted
the header as `false` and pack stations silently lost the scale. Doing
the PNA header in outer ASGI middleware is the fix.)

## Driver model

Each device is a **driver**: a class that owns one device family, exposes
the HTTP routes that operate it, and reports liveness. Drivers are
declared in `enabled_drivers`; the app builds them from the registry and
mounts their routes. Adding a device is: write a `Driver` subclass with a
`from_settings` factory and a `build_router`, then register it in
`hwbridge/drivers/__init__.py`.

| Driver | Device | Transport | Routes |
|---|---|---|---|
| `escpos_usb` | ESC/POS receipt printer + cash drawer | raw USB (python-escpos / libusb) | `POST /print`, `POST /open-drawer`, `POST /test-print` |
| `hid_scale` | USB HID shipping scale | raw USB HID (hidapi) | `GET /scale` |
| `zebra_zpl` | Zebra ZPL label printer | Windows print share (UNC) | `POST /label`, `POST /label/bin-sticker`, `POST /label/item-barcode` |

Connections open lazily on first use, so importing the package and
building the app never touches hardware -- the app boots fine on dev/CI
machines with no devices attached.

## Platform

Targeted at **Windows** stations: autostart via Task Scheduler, the cash
drawer kick, and the Zebra print-share transport are Windows-shaped. The
USB-HID and ESC/POS code is cross-platform, but the deployment story here
is Windows.
