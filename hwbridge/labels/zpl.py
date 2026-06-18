"""ZPL label builders.

Emit ZPL (Zebra Programming Language) as text for two common label
stocks. The output is handed to the ``zebra_zpl`` driver, which streams
the bytes to the printer. Sizes are fixed to the stocks these were built
for; adjust the dot dimensions for other label sizes.
"""

from __future__ import annotations

from typing import Optional


def bin_sticker_zpl(sku: str, upc: Optional[str]) -> str:
    """4x2 inch (812x406 dots @ 203 DPI) bin sticker.

    SKU is centered at the top in large text; a UPC, when present, renders
    below as a Code 128 barcode with human-readable digits. With no UPC the
    layout falls back to a larger SKU-only label so it doesn't look empty.
    """
    safe_sku = (sku or "").replace('"', '\\"').replace("^", " ")
    upc_clean = (upc or "").strip()
    if upc_clean and upc_clean.lower() not in ("none", "nan"):
        safe_upc = upc_clean.replace('"', '\\"').replace("^", " ")
        return (
            "^XA\n"
            "^PW812\n"
            "^LL406\n"
            "^PON\n"
            "^FO20,40\n"
            "^A0N,80,80\n"
            "^FB772,3,0,C\n"
            f"^FD{safe_sku}^FS\n"
            "^FO60,210\n"
            "^BCN,130,Y,N,N\n"
            f"^FD{safe_upc}^FS\n"
            "^XZ"
        )
    return (
        "^XA\n"
        "^PW812\n"
        "^LL406\n"
        "^PON\n"
        "^FO20,138\n"
        "^A0N,100,100\n"
        "^FB772,3,0,C\n"
        f"^FD{safe_sku}^FS\n"
        "^XZ"
    )


def item_barcode_zpl(upc: str) -> str:
    """1.5x1 inch (304x203 dots @ 203 DPI) item barcode label.

    UPC-A symbology with a human-readable digit row, for small items whose
    vendor barcode is missing or too small to scan reliably.
    """
    safe_upc = (upc or "").strip().replace('"', '\\"').replace("^", " ")
    return (
        "^XA^PW304^LL203^LH0,0"
        f"^BY2^FO57,15^BUN,140,Y,N,Y^FD{safe_upc}^FS"
        "^XZ\n"
    )


def item_barcode_zpl_bulk(upc: str, quantity: int) -> str:
    """Concatenate the 1.5x1 label ``quantity`` times so a single Zebra job
    emits a strip. Quantity is clamped to 1..100."""
    qty = max(1, min(100, int(quantity)))
    return item_barcode_zpl(upc) * qty
