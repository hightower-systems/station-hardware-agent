"""ZPL builder + Zebra send tests. The send path uses an injected runner."""

from __future__ import annotations

import pytest

from hwbridge.drivers.zebra_zpl import ZebraZplDriver
from hwbridge.labels.zpl import (
    bin_sticker_zpl,
    item_barcode_zpl,
    item_barcode_zpl_bulk,
)


def test_bin_sticker_with_upc_has_barcode():
    zpl = bin_sticker_zpl("SKU-123", "012345678905")
    assert zpl.startswith("^XA")
    assert zpl.endswith("^XZ")
    assert "SKU-123" in zpl
    assert "^BCN" in zpl          # Code 128
    assert "012345678905" in zpl


def test_bin_sticker_without_upc_is_sku_only():
    zpl = bin_sticker_zpl("SKU-123", None)
    assert "SKU-123" in zpl
    assert "^BCN" not in zpl       # no barcode in the fallback layout


def test_item_barcode_is_upc_a():
    zpl = item_barcode_zpl("012345678905")
    assert "^BUN" in zpl           # UPC-A
    assert "012345678905" in zpl


def test_item_barcode_bulk_repeats():
    zpl = item_barcode_zpl_bulk("012345678905", 3)
    assert zpl.count("^XA") == 3


class _FakeProc:
    def __init__(self, returncode: int = 0, stderr: bytes = b"") -> None:
        self.returncode = returncode
        self.stderr = stderr


def test_send_zpl_copies_to_target():
    calls: list[list[str]] = []

    def runner(args, **kwargs) -> _FakeProc:
        calls.append(args)
        return _FakeProc(returncode=0)

    driver = ZebraZplDriver(target=r"\\HOST\ZEBRA", runner=runner)
    driver.send_zpl(b"^XA^XZ")

    assert calls, "runner should have been invoked"
    assert calls[0][:4] == ["cmd", "/c", "copy", "/B"]
    assert calls[0][-1] == r"\\HOST\ZEBRA"


def test_send_zpl_raises_on_nonzero_exit():
    def runner(args, **kwargs) -> _FakeProc:
        return _FakeProc(returncode=1, stderr=b"share not found")

    driver = ZebraZplDriver(target=r"\\HOST\ZEBRA", runner=runner)
    with pytest.raises(RuntimeError):
        driver.send_zpl(b"^XA^XZ")
