"""Entry point: ``python -m hwbridge`` (or the ``hwbridge`` console script).

Builds the app from settings, optionally prints a startup test receipt,
starts the tray icon, and serves the agent with uvicorn.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime

import uvicorn

from hwbridge import __version__
from hwbridge.app import create_app, get_drivers
from hwbridge.config import get_settings
from hwbridge.drivers.escpos_usb import EscposUsbDriver

log = logging.getLogger(__name__)


def _escpos_driver() -> EscposUsbDriver | None:
    for d in get_drivers():
        if isinstance(d, EscposUsbDriver):
            return d
    return None


def _maybe_start_tray(settings) -> None:
    if not settings.tray_icon_enabled:
        return
    try:
        from hwbridge import tray
    except Exception:
        log.warning("tray dependencies missing; continuing without it")
        return

    def _online() -> bool:
        return any(d.is_online() for d in get_drivers())

    def _on_test_print() -> None:
        driver = _escpos_driver()
        if driver is not None:
            driver.printer.print_text(
                f"Tray test print\n{datetime.now(UTC).replace(tzinfo=None):%Y-%m-%d %H:%M:%S}\n",
                cut=True,
            )

    def _on_quit() -> None:
        for d in get_drivers():
            try:
                d.close()
            except Exception:
                log.exception("driver close on quit failed")
        os._exit(0)

    try:
        icon = tray.build_tray_icon(
            online_getter=_online,
            on_test_print=_on_test_print,
            on_quit=_on_quit,
        )
        tray.run_in_thread(icon)
    except Exception:
        log.warning("tray icon could not start (likely headless); continuing")


def main() -> None:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    app = create_app(settings)

    if settings.print_test_on_startup:
        driver = _escpos_driver()
        if driver is not None:
            try:
                driver.printer.print_text(
                    f"Station Hardware Agent v{__version__} online.\n", cut=True
                )
            except Exception:
                log.warning("startup test print failed")

    _maybe_start_tray(settings)

    uvicorn.run(
        app,
        host=settings.listen_host,
        port=settings.listen_port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
