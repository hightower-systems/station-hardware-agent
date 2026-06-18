"""App-level tests: origin pinning, status, PNA preflight, driver routing."""

from __future__ import annotations

from tests.conftest import ALLOWED


def test_status_requires_allowed_origin(client):
    resp = client.get("/status", headers={"Origin": "http://evil.example.com"})
    assert resp.status_code == 403
    assert resp.json() == {"error": "forbidden_origin"}


def test_status_ok_with_allowed_origin(client, headers):
    resp = client.get("/status", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["agent"] == "online"
    assert "escpos_usb" in body["drivers"]
    assert body["drivers"]["escpos_usb"] is True  # fake printer reports online


def test_print_routes_to_escpos_driver(client, headers, fake_escpos):
    resp = client.post(
        "/print",
        headers=headers,
        json={"format": "text", "content": "receipt body", "cut": True},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True
    assert fake_escpos.printed == ["receipt body"]
    assert fake_escpos.cuts == ["PART"]


def test_print_rejects_image_format(client, headers):
    # This agent prints ESC/POS text only; image format must be rejected.
    resp = client.post(
        "/print",
        headers=headers,
        json={"format": "image", "content": "..."},
    )
    assert resp.status_code == 422


def test_open_drawer(client, headers, fake_escpos):
    resp = client.post("/open-drawer", headers=headers)
    assert resp.status_code == 200
    assert fake_escpos.drawer_kicks == [2]


def test_pna_header_on_preflight(client):
    resp = client.options(
        "/print",
        headers={
            "Origin": ALLOWED,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Private-Network": "true",
        },
    )
    assert resp.headers.get("access-control-allow-private-network") == "true"
