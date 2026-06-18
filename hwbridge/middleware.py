"""HTTP middleware for the localhost hardware bridge.

The agent's only security model is "exactly one web origin, from this
machine, may drive the hardware." Two pieces enforce and enable that:

1. Origin pinning (in ``app.py``): every non-preflight request must carry
   an ``Origin`` equal to ``allowed_origin`` or it is rejected 403.
   Together with binding to 127.0.0.1, only the one web app you name can
   reach the agent, and only from the machine it runs on.

2. Private Network Access (this file): Chrome/Edge 117+ send a CORS
   preflight with ``Access-Control-Request-Private-Network: true`` when an
   HTTPS public-origin page fetches ``http://127.0.0.1``. The browser
   drops the call unless the preflight response echoes
   ``Access-Control-Allow-Private-Network: true``.

This is implemented as pure ASGI middleware, mounted *outermost*, so the
CORS middleware cannot strip or overwrite the header on the way out --
the exact ordering bug that bit the original Flask agent, where
flask-cors's own response hook clobbered the header back to ``false``.

PNA is being superseded by Local Network Access (LNA), which moves the
decision to a client-side permission/flag/enterprise policy. The header
below still satisfies older Chrome/Edge; see ``docs/browser-setup.md``
for the LNA story users must handle on their end.
"""

from __future__ import annotations

from starlette.types import ASGIApp, Message, Receive, Scope, Send

_PNA_HEADER = b"access-control-allow-private-network"


class PrivateNetworkAccessMiddleware:
    def __init__(self, app: ASGIApp, allowed_origin: str) -> None:
        self.app = app
        self.allowed_origin = allowed_origin.encode("latin-1")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        if headers.get(b"origin") != self.allowed_origin:
            await self.app(scope, receive, send)
            return

        async def send_with_pna(message: Message) -> None:
            if message["type"] == "http.response.start":
                raw = [
                    (k, v)
                    for (k, v) in message.get("headers", [])
                    if k.lower() != _PNA_HEADER
                ]
                raw.append((_PNA_HEADER, b"true"))
                message = {**message, "headers": raw}
            await send(message)

        await self.app(scope, receive, send_with_pna)
