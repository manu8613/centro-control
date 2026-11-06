"""Counters, meters and integrators."""

from __future__ import annotations

from datetime import date

import pytest

from custom_components.centro_control.energy import (
    Counters,
    Integrator,
    Meter,
    period_end,
    period_start,
    to_kwh,
    to_watts,
)


def test_units():
    assert to_watts(1.5, "kW") == 1500
    assert to_watts(300, "W") == 300
    assert to_kwh(2500, "Wh") == 2.5
    assert to_kwh(1, "MWh") == 1000


@pytest.mark.parametrize(
    ("day", "billing", "expected"),
    [
        (date(2026, 11, 6), 1, date(2026, 11, 1)),
        (date(2026, 11, 6), 15, date(2026, 10, 15)),
        (date(2026, 1, 3), 21, date(2025, 12, 21)),
        (date(2026, 11, 21), 21, date(2026, 11, 21)),
    ],
)
def test_period_start(day, billing, expected):
    assert period_start(day, billing) == expected


def test_period_end():
    assert period_end(date(2026, 12, 21)) == date(2027, 1, 21)


def test_counters_roll_and_history():
    c = Counters(billing_day=5)
    c.add("solar", 10, date(2026, 11, 3))
    c.add("solar", 2, date(2026, 11, 3))
    assert c.get("solar") == 12
    c.add("solar", 5, date(2026, 11, 4))
    assert c.get("solar", "hoy") == 5
    assert c.get("solar", "ayer") == 12
    assert c.get("solar", "mes") == 17
    assert c.get("solar", "factura") == 17  # period started 5 Oct
    c.add("solar", 1, date(2026, 11, 5))  # new billing period
    assert c.get("solar", "factura") == 1
    assert c.get("solar", "mes") == 18
    c.add("solar", 1, date(2026, 12, 1))
    assert c.get("solar", "mes") == 1
    assert c.get("solar", "ano") == 19
    assert c.get("solar", "total") == 19
    assert c.history["2026-11-03"]["solar"] == 12
    # roundtrip
    again = Counters.from_dict(c.as_dict(), 5)
    assert again.get("solar", "total") == 19
    assert again.history == c.history


def test_counters_months_and_days():
    c = Counters()
    c.add("solar", 3, date(2026, 10, 30))
    c.add("solar", 4, date(2026, 11, 1))
    c.add("solar", 6, date(2026, 11, 2))
    months = dict(c.months("solar", 2, date(2026, 11, 2)))
    assert months == {"2026-10": 3, "2026-11": 10}
    days = c.days("solar", 3, date(2026, 11, 2))
    assert days == [("2026-10-31", 0), ("2026-11-01", 4), ("2026-11-02", 6)]


def test_billing_day_change_rebuilds_period():
    c = Counters(billing_day=1)
    for d in range(1, 11):
        c.add("importada", 1, date(2026, 11, d))
    c.set_billing_day(5, date(2026, 11, 10))
    assert c.get("importada", "factura") == 6  # 5..10


def test_meter_increments_resets_and_spikes():
    m = Meter(max_kw=20)
    assert m.update(100.0, 0) == 0  # first reading only sets the baseline
    assert m.update(100.5, 600) == pytest.approx(0.5)
    assert m.update(0.0, 1200) == 0  # daily reset
    assert m.update(0.2, 1800) == pytest.approx(0.2)
    assert m.update(5000, 1860) == 0  # impossible jump
    assert m.update(5000.1, 2460) == pytest.approx(0.1)


def test_integrator_trapezoid_and_gaps():
    i = Integrator(max_gap=120)
    total = 0.0
    for t in range(0, 3601, 10):
        total += i.sample(1000.0, t)
    assert total == pytest.approx(1.0)
    assert i.sample(1000.0, 3601 + 500) == 0  # gap too long
    assert i.sample(None, 5000) == 0


def test_import_days_fills_history_and_buckets():
    c = Counters(billing_day=1)
    c.add("solar", 2, date(2026, 11, 6))
    added = c.import_days(
        {
            "2026-11-03": {"solar": 10},
            "2026-10-15": {"solar": 5},
            "2025-11-03": {"solar": 7},
            "2026-11-06": {"solar": 99},  # today: ignored
        },
        date(2026, 11, 6),
    )
    assert added == 3
    assert c.get("solar", "hoy") == 2
    assert c.get("solar", "mes") == 12
    assert c.get("solar", "factura") == 12
    assert c.get("solar", "ano") == 17
    assert c.get("solar", "total") == 24
    assert c.import_days({"2026-11-03": {"solar": 10}}, date(2026, 11, 6)) == 0  # not twice
