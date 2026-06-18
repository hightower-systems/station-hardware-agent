"""ESC/POS USB wrapper tests: lock-serialized writes and single reconnect."""

from __future__ import annotations

from hwbridge.drivers.escpos_usb import EscposUsbPrinter
from tests.conftest import FakeEscpos


def test_print_text_writes_and_cuts():
    fake = FakeEscpos()
    printer = EscposUsbPrinter(fake)
    printer.print_text("hello", cut=True)
    assert fake.printed == ["hello"]
    assert fake.cuts == ["PART"]


def test_print_text_without_cut():
    fake = FakeEscpos()
    printer = EscposUsbPrinter(fake)
    printer.print_text("hello", cut=False)
    assert fake.printed == ["hello"]
    assert fake.cuts == []


def test_open_drawer_kicks_pin():
    fake = FakeEscpos()
    printer = EscposUsbPrinter(fake)
    printer.open_drawer(pin=5)
    assert fake.drawer_kicks == [5]


def test_reconnect_on_transient_failure():
    fakes: list[FakeEscpos] = []

    def connect() -> FakeEscpos:
        f = FakeEscpos()
        fakes.append(f)
        return f

    printer = EscposUsbPrinter(connect=connect)
    printer._ensure()              # connects fakes[0]
    fakes[0].fail_text_once = True  # first write fails, triggering reconnect

    printer.print_text("after-reconnect")

    assert fakes[0].closed is True
    assert fakes[1].printed == ["after-reconnect"]


def test_is_online_false_when_connect_fails():
    def connect() -> FakeEscpos:
        raise RuntimeError("no device")

    printer = EscposUsbPrinter(connect=connect)
    assert printer.is_online() is False
