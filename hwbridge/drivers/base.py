"""Driver base class.

A driver owns one physical device (or device family): it exposes the
HTTP routes that operate the device and reports liveness. Subclasses set
``name``, provide a ``from_settings`` factory, and implement
``build_router``. ``is_online`` and ``close`` have no-op defaults for
stateless devices (e.g. a label printer reached over a print share).
"""

from __future__ import annotations

from fastapi import APIRouter


class Driver:
    name: str = "driver"

    def build_router(self) -> APIRouter:
        raise NotImplementedError

    def is_online(self) -> bool:
        return True

    def close(self) -> None:
        pass
