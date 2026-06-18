"""System-tray status icon (optional).

A small green/red tray icon so an operator can see the agent is up and
trigger a test print without a terminal. pystray is imported lazily so
the agent still boots on headless machines / CI where no tray backend
exists.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

from PIL import Image, ImageDraw

from hwbridge import __version__

log = logging.getLogger(__name__)


def make_icon_image(*, online: bool = True) -> Image.Image:
    """64x64 status glyph. Green when online, red when offline."""
    bg = (32, 130, 79) if online else (160, 50, 50)
    img = Image.new("RGB", (64, 64), color=bg)
    draw = ImageDraw.Draw(img)
    draw.rectangle((10, 14, 54, 50), fill=(255, 255, 255))
    draw.rectangle((10, 14, 54, 22), fill=bg)
    draw.line((16, 30, 48, 30), fill=bg, width=2)
    draw.line((16, 36, 48, 36), fill=bg, width=2)
    draw.line((16, 42, 40, 42), fill=bg, width=2)
    return img


def status_text(online: bool) -> str:
    return "Hardware: online" if online else "Hardware: offline"


def build_tray_icon(
    *,
    online_getter: Callable[[], bool],
    on_test_print: Callable[[], None],
    on_quit: Callable[[], None],
):
    """Construct a pystray Icon. Imported lazily so the agent can boot on
    headless runners where pystray's platform backend isn't available."""
    import pystray  # noqa: PLC0415  -- intentionally lazy

    def _status_label(_item) -> str:
        return status_text(online_getter())

    def _test_print(icon, _item) -> None:
        try:
            on_test_print()
        except Exception:
            log.exception("tray test-print failed")

    def _quit(icon, _item) -> None:
        try:
            on_quit()
        finally:
            icon.stop()

    return pystray.Icon(
        "station-hardware-agent",
        make_icon_image(online=True),
        f"Station Hardware Agent v{__version__}",
        menu=pystray.Menu(
            pystray.MenuItem(_status_label, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Test print", _test_print),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", _quit),
        ),
    )


def run_in_thread(icon) -> threading.Thread:
    """Run the tray event loop on a daemon thread; it exits with the process."""
    t = threading.Thread(target=icon.run, name="tray-icon", daemon=True)
    t.start()
    return t
