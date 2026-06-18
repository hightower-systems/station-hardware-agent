"""Zebra ZPL label-printer driver.

Streams raw ZPL to a Zebra label printer exposed as a Windows print
share (UNC path), the way pack stations reach it: write the bytes to a
temp file and ``copy /B`` it to the share. The target defaults to
``\\\\<this-machine-ip>\\ZEBRA`` when not configured, matching the
common host-local share convention; set ``zebra_target`` for a
network-shared printer (``\\\\SERVER\\QUEUE``).

Two route styles are exposed: ``POST /label`` accepts raw ZPL bytes
(for callers that build their own labels), and ``/label/bin-sticker`` /
``/label/item-barcode`` build ZPL server-side from the ``labels.zpl``
templates.
"""

from __future__ import annotations

import logging
import os
import socket
import subprocess
import tempfile
from typing import Any, Callable, Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from hwbridge.config import Settings
from hwbridge.drivers.base import Driver
from hwbridge.labels.zpl import bin_sticker_zpl, item_barcode_zpl_bulk

log = logging.getLogger(__name__)


def _local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class BinStickerRequest(BaseModel):
    sku: str
    upc: Optional[str] = None


class ItemBarcodeRequest(BaseModel):
    upc: str
    quantity: int = Field(default=1, ge=1, le=100)


class ZebraZplDriver(Driver):
    name = "zebra_zpl"

    def __init__(
        self,
        *,
        target: str,
        runner: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.target = target
        self._runner = runner or subprocess.run

    @classmethod
    def from_settings(cls, settings: Settings) -> "ZebraZplDriver":
        target = settings.zebra_target.strip() or f"\\\\{_local_ip()}\\ZEBRA"
        return cls(target=target)

    def send_zpl(self, zpl: bytes) -> None:
        """Write ZPL to a temp file and copy it to the printer share."""
        fd, path = tempfile.mkstemp(suffix=".zpl")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(zpl)
            proc = self._runner(
                ["cmd", "/c", "copy", "/B", path, self.target],
                check=False,
                capture_output=True,
                timeout=10,
            )
            if proc.returncode != 0:
                stderr = (proc.stderr or b"").decode(errors="ignore").strip()
                raise RuntimeError(
                    f"copy to {self.target} failed (code {proc.returncode}): {stderr}"
                )
            log.info("label sent to Zebra (%d bytes)", len(zpl))
        finally:
            try:
                os.remove(path)
            except Exception:
                pass

    def build_router(self) -> APIRouter:
        router = APIRouter()

        @router.post("/label")
        async def print_label(request: Request) -> dict[str, Any]:
            data = await request.body()
            if not data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"error": "no_zpl"},
                )
            self._send_or_503(data)
            return {"status": "success", "message": "Label sent to printer"}

        @router.post("/label/bin-sticker")
        def print_bin_sticker(body: BinStickerRequest) -> dict[str, Any]:
            zpl = bin_sticker_zpl(body.sku, body.upc)
            self._send_or_503(zpl.encode("utf-8"))
            return {"status": "success", "message": "Bin sticker sent"}

        @router.post("/label/item-barcode")
        def print_item_barcode(body: ItemBarcodeRequest) -> dict[str, Any]:
            zpl = item_barcode_zpl_bulk(body.upc, body.quantity)
            self._send_or_503(zpl.encode("utf-8"))
            return {"status": "success", "message": f"{body.quantity} label(s) sent"}

        return router

    def _send_or_503(self, zpl: bytes) -> None:
        try:
            self.send_zpl(zpl)
        except subprocess.TimeoutExpired as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"error": "printer_timeout", "message": "check the Zebra printer"},
            ) from exc
        except Exception as exc:
            log.exception("zebra print failed")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"error": "printer_offline", "message": str(exc)},
            ) from exc
