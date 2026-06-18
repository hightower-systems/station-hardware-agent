"""HID scale wire-protocol tests. Pure parsing, no hardware."""

from __future__ import annotations

from hwbridge.drivers.hid_scale import parse_scale_report


def test_stable_ounces_converted_to_pounds():
    # status=4 (stable), unit=11 (ounces), exponent=-1, raw=160 -> 16.0 oz = 1.0 lb
    report = [3, 4, 11, 255, 160, 0]
    result = parse_scale_report(report)
    assert result == {"weight": 1.0, "unit": "lbs", "stable": True}


def test_unstable_flag():
    report = [3, 2, 11, 255, 160, 0]  # status != 4
    result = parse_scale_report(report)
    assert result is not None
    assert result["stable"] is False


def test_pounds_unit_is_not_divided_by_16():
    # unit=12 (pounds), exponent=-1, raw=50 -> 5.0 lb, no /16 conversion
    report = [3, 4, 12, 255, 50, 0]
    result = parse_scale_report(report)
    assert result is not None
    assert result["weight"] == 5.0


def test_floor_at_one_ounce():
    report = [3, 4, 11, 0, 0, 0]  # zero weight -> floored to 0.0625 lb
    result = parse_scale_report(report)
    assert result is not None
    assert result["weight"] == 0.0625


def test_empty_or_short_report_is_none():
    assert parse_scale_report([]) is None
    assert parse_scale_report([3, 4, 11]) is None
