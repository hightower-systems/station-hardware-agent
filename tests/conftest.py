from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from hwbridge.app import create_app, get_drivers
from hwbridge.config import Settings
from hwbridge.drivers.escpos_usb import EscposUsbDriver, EscposUsbPrinter

ALLOWED = "http://pos-vm.local:8080"


class FakeEscpos:
    """Stand-in for python-escpos's Usb printer; no hardware required."""

    def __init__(self) -> None:
        self.printed: list[str] = []
        self.cuts: list[str] = []
        self.drawer_kicks: list[int] = []
        self.online: bool = True
        self.fail_text_once: bool = False
        self.fail_text_always: bool = False
        self.closed: bool = False

    def text(self, text: str) -> None:
        if self.fail_text_always:
            raise RuntimeError("USB write failed")
        if self.fail_text_once:
            self.fail_text_once = False
            raise RuntimeError("USB write failed (transient)")
        self.printed.append(text)

    def cut(self, mode: str = "PART") -> None:
        self.cuts.append(mode)

    def cashdraw(self, pin: int) -> None:
        self.drawer_kicks.append(pin)

    def is_online(self) -> bool:
        return self.online

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def settings() -> Settings:
    return Settings(
        allowed_origin=ALLOWED,
        enabled_drivers=["escpos_usb"],
        tray_icon_enabled=False,
        print_test_on_startup=False,
    )


@pytest.fixture
def fake_escpos() -> FakeEscpos:
    return FakeEscpos()


@pytest.fixture
def client(settings: Settings, fake_escpos: FakeEscpos) -> Generator[TestClient, None, None]:
    app = create_app(settings)
    # Swap the lazily-connecting USB printer for a pre-connected fake.
    for d in get_drivers():
        if isinstance(d, EscposUsbDriver):
            d.printer = EscposUsbPrinter(fake_escpos)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def headers() -> dict[str, str]:
    return {"Origin": ALLOWED}
