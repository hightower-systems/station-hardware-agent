"""Driver registry.

Maps a driver name (as used in ``enabled_drivers``) to a factory that
builds it from settings. To add a device, implement a ``Driver`` subclass
with a ``from_settings`` classmethod and register it here.
"""

from __future__ import annotations

from collections.abc import Callable

from hwbridge.config import Settings
from hwbridge.drivers.base import Driver
from hwbridge.drivers.escpos_usb import EscposUsbDriver
from hwbridge.drivers.hid_scale import HidScaleDriver
from hwbridge.drivers.zebra_zpl import ZebraZplDriver

REGISTRY: dict[str, Callable[[Settings], Driver]] = {
    "escpos_usb": EscposUsbDriver.from_settings,
    "hid_scale": HidScaleDriver.from_settings,
    "zebra_zpl": ZebraZplDriver.from_settings,
}


def build_drivers(settings: Settings) -> list[Driver]:
    drivers: list[Driver] = []
    for name in settings.enabled_drivers:
        factory = REGISTRY.get(name)
        if factory is None:
            raise ValueError(
                f"unknown driver '{name}'. Known drivers: {sorted(REGISTRY)}"
            )
        drivers.append(factory(settings))
    return drivers
