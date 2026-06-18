"""Agent configuration.

Values are read from the environment and an optional local ``.env``
file. Everything has a safe default except ``allowed_origin``, which you
must set to the exact origin of the web app permitted to talk to this
agent (scheme + host + port, no trailing slash).
"""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # -- HTTP listener -----------------------------------------------------
    listen_host: str = "127.0.0.1"
    listen_port: int = 8765
    # The one web origin allowed to drive the local hardware. Set this.
    allowed_origin: str = "http://localhost:8080"

    # -- which device drivers to load (comma-separated in .env) -----------
    enabled_drivers: list[str] = ["escpos_usb"]

    # -- escpos_usb: ESC/POS receipt printer + cash drawer over USB -------
    escpos_vendor_id: int = 0x0519       # Star Micronics
    escpos_product_id: int = 0x0001      # TSP100 family
    escpos_profile: str = "TSP100"
    drawer_pin: int = 2

    # -- hid_scale: USB HID shipping scale --------------------------------
    scale_vendor_id: int = 0x0B67        # Mettler-Toledo (common OEM)
    scale_product_id: int = 0x555E

    # -- zebra_zpl: raw ZPL label printer ---------------------------------
    # A Windows print-share UNC path (e.g. \\\\HOST\\ZEBRA). Leave blank to
    # auto-detect \\\\<this-machine-ip>\\ZEBRA.
    zebra_target: str = ""

    # -- runtime ----------------------------------------------------------
    print_test_on_startup: bool = False
    tray_icon_enabled: bool = True
    log_level: str = "INFO"

    @field_validator("enabled_drivers", mode="before")
    @classmethod
    def _split_csv(cls, v: object) -> object:
        # Allow `ENABLED_DRIVERS=escpos_usb,hid_scale` in .env as well as JSON.
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

    @field_validator(
        "escpos_vendor_id",
        "escpos_product_id",
        "scale_vendor_id",
        "scale_product_id",
        mode="before",
    )
    @classmethod
    def _parse_int(cls, v: object) -> object:
        # USB ids are conventionally hex; accept `0x0519` (or decimal) in .env.
        if isinstance(v, str):
            return int(v.strip(), 0)
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
