"""ESC/POS receipt-printer driver (USB transport).

Drives an ESC/POS thermal receipt printer and its daisy-chained cash
drawer over raw USB via python-escpos. Writes are serialized behind a
lock so concurrent requests can't interleave bytes on the wire, and a
single reconnect is attempted on transient USB failures (the printer was
power-cycled, or ran out of paper and was reloaded).

The connection is opened lazily on first use, so importing this module
(and constructing the app) never touches hardware -- handy for dev, CI,
and the module-level ``app`` object.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from threading import Lock
from typing import Any, Callable, Optional, Protocol

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from hwbridge import __version__
from hwbridge.config import Settings
from hwbridge.drivers.base import Driver

log = logging.getLogger(__name__)


class _PrinterDriver(Protocol):
    """The subset of python-escpos's Usb printer we depend on."""

    def text(self, text: str) -> None: ...
    def cut(self, mode: str = "PART") -> None: ...
    def cashdraw(self, pin: int) -> None: ...
    def is_online(self) -> bool: ...
    def close(self) -> None: ...


class EscposUsbPrinter:
    """Lock-serialized wrapper around a python-escpos USB printer that
    connects lazily and reconnects once on transient USB failures."""

    def __init__(
        self,
        driver: Optional[_PrinterDriver] = None,
        *,
        connect: Optional[Callable[[], _PrinterDriver]] = None,
    ) -> None:
        self._driver = driver
        self._connect = connect
        self._lock = Lock()

    @classmethod
    def open_usb(cls, *, vendor_id: int, product_id: int, profile: str) -> "EscposUsbPrinter":
        def _connect() -> _PrinterDriver:
            from escpos.printer import Usb

            return Usb(vendor_id, product_id, profile=profile)

        return cls(connect=_connect)  # lazy; not connected until first use

    def _ensure(self) -> _PrinterDriver:
        if self._driver is None:
            if self._connect is None:
                raise RuntimeError("printer not connected and no connect fn")
            self._driver = self._connect()
        return self._driver

    def print_text(self, text: str, *, cut: bool = True) -> None:
        with self._lock:
            try:
                d = self._ensure()
                d.text(text)
                if cut:
                    d.cut(mode="PART")
            except Exception:
                self._try_reconnect()
                d = self._ensure()
                d.text(text)
                if cut:
                    d.cut(mode="PART")

    def open_drawer(self, *, pin: int = 2) -> None:
        with self._lock:
            try:
                self._ensure().cashdraw(pin)
            except Exception:
                self._try_reconnect()
                self._ensure().cashdraw(pin)

    def is_online(self) -> bool:
        try:
            return bool(self._ensure().is_online())
        except Exception:
            return False

    def close(self) -> None:
        if self._driver is None:
            return
        try:
            self._driver.close()
        except Exception:
            log.exception("printer close failed")
        finally:
            self._driver = None

    def _try_reconnect(self) -> None:
        if self._connect is None:
            raise RuntimeError("no reconnect function configured")
        log.warning("printer call failed; attempting reconnect")
        if self._driver is not None:
            try:
                self._driver.close()
            except Exception:
                pass
        self._driver = None
        self._ensure()


class PrintRequest(BaseModel):
    # Text only: this driver prints ESC/POS text, not bitmaps.
    format: str = Field(default="text", pattern="^(text)$")
    content: str
    cut: bool = True
    open_drawer_after: bool = False


class EscposUsbDriver(Driver):
    name = "escpos_usb"

    def __init__(self, *, printer: EscposUsbPrinter, drawer_pin: int = 2) -> None:
        self.printer = printer
        self.drawer_pin = drawer_pin

    @classmethod
    def from_settings(cls, settings: Settings) -> "EscposUsbDriver":
        printer = EscposUsbPrinter.open_usb(
            vendor_id=settings.escpos_vendor_id,
            product_id=settings.escpos_product_id,
            profile=settings.escpos_profile,
        )
        return cls(printer=printer, drawer_pin=settings.drawer_pin)

    def is_online(self) -> bool:
        return self.printer.is_online()

    def close(self) -> None:
        self.printer.close()

    def build_router(self) -> APIRouter:
        router = APIRouter()

        @router.post("/print")
        def print_endpoint(body: PrintRequest) -> dict[str, Any]:
            try:
                self.printer.print_text(body.content, cut=body.cut)
                if body.open_drawer_after:
                    self.printer.open_drawer(pin=self.drawer_pin)
            except Exception as exc:
                log.exception("print failed")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={"error": "printer_offline", "message": str(exc)},
                ) from exc
            return {"success": True, "printer_status": "ok"}

        @router.post("/open-drawer")
        def open_drawer_endpoint() -> dict[str, Any]:
            try:
                self.printer.open_drawer(pin=self.drawer_pin)
            except Exception as exc:
                log.exception("open-drawer failed")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={"error": "drawer_offline", "message": str(exc)},
                ) from exc
            return {"success": True}

        @router.post("/test-print")
        def test_print_endpoint() -> dict[str, Any]:
            body = (
                "Station Hardware Agent\n"
                f"Version: {__version__}\n"
                f"{datetime.now(UTC).replace(tzinfo=None):%Y-%m-%d %H:%M:%S}\n"
                "If you can read this, the\nprinter is wired correctly.\n"
            )
            try:
                self.printer.print_text(body, cut=True)
            except Exception as exc:
                log.exception("test-print failed")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={"error": "printer_offline", "message": str(exc)},
                ) from exc
            return {"success": True, "printer_status": "ok"}

        return router
