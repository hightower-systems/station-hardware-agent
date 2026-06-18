# Devices

Enable the drivers you need via `ENABLED_DRIVERS` (comma-separated). Each
driver has its own config keys in `.env`.

## escpos_usb -- ESC/POS receipt printer + cash drawer

Prints **ESC/POS text** receipts over raw USB (python-escpos / libusb)
and kicks a cash drawer daisy-chained off the printer. Writes are
serialized behind a lock and reconnect once on a transient USB error.

| Key | Default | Notes |
|---|---|---|
| `ESCPOS_VENDOR_ID` | `0x0519` | USB vendor id (Star Micronics) |
| `ESCPOS_PRODUCT_ID` | `0x0001` | USB product id (TSP100 family) |
| `ESCPOS_PROFILE` | `TSP100` | python-escpos capabilities profile |
| `DRAWER_PIN` | `2` | ESC/POS drawer pin (some setups use 5) |

Routes: `POST /print` `{format:"text", content, cut, open_drawer_after}`,
`POST /open-drawer`, `POST /test-print`.

> Driver note: Windows raw-USB access needs a libusb-compatible driver
> bound to the printer (e.g. via Zadig / WinUSB). If `/print` returns
> `printer_offline`, the device is usually claimed by the wrong driver.

## hid_scale -- USB HID shipping scale

Reads weight from a USB HID scale using the standard HID "Scale" usage
page (Mettler-Toledo, DYMO, and many OEM postal scales). Returns pounds.

| Key | Default | Notes |
|---|---|---|
| `SCALE_VENDOR_ID` | `0x0b67` | USB vendor id (Mettler-Toledo) |
| `SCALE_PRODUCT_ID` | `0x555e` | USB product id |

Route: `GET /scale` -> `{status, weight, unit:"lbs", stable}`.

## zebra_zpl -- Zebra ZPL label printer

Streams raw ZPL to a Zebra printer exposed as a Windows print share. Also
builds ZPL server-side for two common label stocks.

| Key | Default | Notes |
|---|---|---|
| `ZEBRA_TARGET` | (blank) | UNC path, e.g. `\\SERVER\ZEBRA`. Blank auto-detects `\\<this-ip>\ZEBRA`. |

Routes: `POST /label` (raw ZPL bytes),
`POST /label/bin-sticker` `{sku, upc?}`,
`POST /label/item-barcode` `{upc, quantity}`.

## Finding a device's vendor/product id

- **Windows:** Device Manager -> the device -> Properties -> Details ->
  "Hardware Ids" shows `VID_xxxx&PID_xxxx`.
- **Cross-platform:** `python -c "import usb.core; [print(hex(d.idVendor), hex(d.idProduct)) for d in usb.core.find(find_all=True)]"`
  (needs pyusb + libusb), or `lsusb` on Linux.

Set the ids in `.env` as hex (`0x...`) or decimal.
