"""FastAPI application factory.

Wires the middleware stack (CORS, origin pin, Private Network Access),
builds the configured drivers, mounts their routes, and exposes a
unified ``/status`` endpoint.

Middleware ordering matters. They are registered CORS -> origin_check ->
PNA, which makes PNA *outermost*: on the way out it appends the
Access-Control-Allow-Private-Network header last, so the CORS middleware
cannot strip or overwrite it (the bug that bit the original Flask agent).
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from hwbridge import __version__
from hwbridge.config import Settings, get_settings
from hwbridge.drivers import build_drivers
from hwbridge.drivers.base import Driver
from hwbridge.middleware import PrivateNetworkAccessMiddleware

log = logging.getLogger(__name__)

_drivers: list[Driver] = []


def set_drivers(drivers: list[Driver]) -> None:
    global _drivers
    _drivers = drivers


def get_drivers() -> list[Driver]:
    return _drivers


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    allowed = settings.allowed_origin

    app = FastAPI(title="station-hardware-agent", version=__version__)

    # Innermost: standard CORS for the one allowed origin.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[allowed],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    # Middle: hard origin pin on real (non-preflight) requests.
    @app.middleware("http")
    async def origin_check(request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)
        if request.headers.get("origin") != allowed:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"error": "forbidden_origin"},
            )
        return await call_next(request)

    # Outermost: PNA header that CORS must not be able to strip.
    app.add_middleware(PrivateNetworkAccessMiddleware, allowed_origin=allowed)

    drivers = build_drivers(settings)
    set_drivers(drivers)
    for driver in drivers:
        app.include_router(driver.build_router())

    @app.get("/status")
    def status_endpoint() -> dict:
        return {
            "agent": "online",
            "version": __version__,
            "drivers": {d.name: d.is_online() for d in get_drivers()},
        }

    return app


app = create_app()
