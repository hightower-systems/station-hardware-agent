"""USB HID shipping-scale driver.

Reads weight from a USB HID scale that speaks the standard HID "Scale"
usage-page data report -- the protocol used by Mettler-Toledo, DYMO and
many OEM USB postal scales. The wire parsing lives in
``parse_scale_report`` so it can be unit-tested without hardware.
"""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter

from hwbridge.config import Settings
from hwbridge.drivers.base import Driver

log = logging.getLogger(__name__)

# 8-byte HID "Scale" data report:
#   [0] report id
#   [1] status     (4 = stable weight)
#   [2] unit code  (11 = ounces, 12 = pounds, 3 = kilograms ...)
#   [3] scale exponent (signed, base-10)
#   [4] weight LSB
#   [5] weight MSB
_STATUS_STABLE = 4
_UNIT_OUNCES = 11
_MIN_WEIGHT_LB = 0.0625  # 1 oz floor, so a settling scale never reports 0


def parse_scale_report(data: list[int]) -> dict | None:
    """Decode an 8-byte HID scale report into pounds.

    The raw count is a signed 16-bit little-endian value scaled by
    ``10**exponent``; ounce readings are converted to pounds and floored
    at one ounce. Returns ``None`` for an empty or too-short report.
    """
    if not data or len(data) < 6:
        return None
    raw_val = data[4] + (data[5] * 256)
    if raw_val > 32767:
        raw_val -= 65536
    exponent = data[3]
    if exponent > 127:
        exponent -= 256
    weight = raw_val * (10 ** exponent)
    if data[2] == _UNIT_OUNCES:
        weight = weight / 16.0
    weight = max(weight, _MIN_WEIGHT_LB)
    return {
        "weight": round(weight, 4),
        "unit": "lbs",
        "stable": data[1] == _STATUS_STABLE,
    }


class HidScaleDriver(Driver):
    name = "hid_scale"

    def __init__(self, *, vendor_id: int, product_id: int) -> None:
        self.vendor_id = vendor_id
        self.product_id = product_id

    @classmethod
    def from_settings(cls, settings: Settings) -> "HidScaleDriver":
        return cls(
            vendor_id=settings.scale_vendor_id,
            product_id=settings.scale_product_id,
        )

    def _read_once(self) -> dict | None:
        import hid

        h = hid.device()
        try:
            h.open(self.vendor_id, self.product_id)
            h.set_nonblocking(1)
            data: list[int] = []
            for _ in range(10):
                d = h.read(8)
                if d:
                    data = d
                    break
                time.sleep(0.01)
        finally:
            try:
                h.close()
            except Exception:
                pass
        return parse_scale_report(data)

    def read_weight(self, *, max_retries: int = 3) -> dict:
        last_err: Exception | None = None
        for attempt in range(max_retries):
            try:
                result = self._read_once()
                if result is not None:
                    log.info(
                        "scale read: %.4f lbs (stable=%s)",
                        result["weight"],
                        result["stable"],
                    )
                    return {"status": "success", **result}
                return {
                    "status": "error",
                    "message": "Scale did not respond. Check power and USB.",
                }
            except Exception as exc:  # device errors are transient; retry
                last_err = exc
                if attempt < max_retries - 1:
                    time.sleep(0.5)
        log.error("scale error after %d retries: %s", max_retries, last_err)
        return {"status": "error", "message": f"Scale error: {last_err}"}

    def is_online(self) -> bool:
        try:
            import hid

            h = hid.device()
            h.open(self.vendor_id, self.product_id)
            h.close()
            return True
        except Exception:
            return False

    def build_router(self) -> APIRouter:
        router = APIRouter()

        @router.get("/scale")
        def read_scale() -> dict:
            return self.read_weight()

        return router
