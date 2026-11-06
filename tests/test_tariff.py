"""2.0TD periods, bill and forecasts."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from custom_components.centro_control.energy import Counters
from custom_components.centro_control.tariff import (
    Scenario,
    Tariff,
    compute_bill,
    current_bill,
    energy_period,
    forecast_current,
    forecast_next,
    power_period,
    simulate,
)


@pytest.mark.parametrize(
    ("moment", "period"),
    [
        (datetime(2026, 11, 9, 11, 0), "P1"),  # Monday
        (datetime(2026, 11, 9, 19, 30), "P1"),
        (datetime(2026, 11, 9, 9, 0), "P2"),
        (datetime(2026, 11, 9, 23, 0), "P2"),
        (datetime(2026, 11, 9, 7, 59), "P3"),
        (datetime(2026, 11, 7, 12, 0), "P3"),  # Saturday
        (datetime(2026, 12, 8, 12, 0), "P3"),  # Inmaculada
    ],
)
def test_energy_period(moment, period):
    assert energy_period(moment) == period


def test_power_period():
    assert power_period(datetime(2026, 11, 9, 9)) == "P1"
    assert power_period(datetime(2026, 11, 9, 7)) == "P2"
    assert power_period(datetime(2026, 11, 8, 12)) == "P2"


def test_bill_matches_hand_calculation():
    t = Tariff(kw_p1=4.6, kw_p2=4.6, power_p1_day=0.075902, power_p2_day=0.001987)
    bill = compute_bill(t, date(2026, 11, 1), date(2026, 12, 1), 30, 300, 200, 45.0, 10.0)
    p1 = 4.6 * 30 * 0.075902
    p2 = 4.6 * 30 * 0.001987
    taxable = p1 + p2 + 45 - 10
    tax = taxable * 0.0511269632
    base = taxable + tax + 30 * t.rental_day + 30 * t.other_day
    assert bill.total_eur == pytest.approx(base * 1.21)
    assert bill.as_dict(t)["lineas"][3]["importe"] == -10.0


def test_compensation_is_capped_at_energy():
    t = Tariff()
    bill = compute_bill(t, date(2026, 6, 1), date(2026, 7, 1), 30, 50, 600, 8.0, 30.0)
    assert bill.compensation_eur == 8.0
    assert bill.compensation_lost_eur == 22.0
    uncapped = compute_bill(Tariff(export_cap=False), date(2026, 6, 1), date(2026, 7, 1), 30, 50, 600, 8.0, 30.0)
    assert uncapped.compensation_eur == 30.0


def _history(c: Counters, start: date, days: int) -> None:
    from datetime import timedelta

    for i in range(days):
        d = start + timedelta(days=i)
        for metric, value in {
            "solar": 10,
            "importada": 5,
            "exportada": 3,
            "consumo": 12,
            "coste_energia": 0.75,
            "compensacion": 0.15,
        }.items():
            c.add(metric, value, d)


def test_current_bill_and_forecast():
    c = Counters(billing_day=1)
    _history(c, date(2026, 10, 1), 36)  # until 5 Nov included
    t = Tariff()
    today = date(2026, 11, 5)
    bill = current_bill(c, t, today)
    assert bill.days == 5
    assert bill.import_kwh == pytest.approx(25)
    end = forecast_current(c, t, today, 1.0)
    assert end.days == 30
    assert end.import_kwh == pytest.approx(150)
    assert end.energy_eur == pytest.approx(150 * 0.15)


def test_forecast_next_uses_model_and_season():
    c = Counters(billing_day=1)
    _history(c, date(2026, 10, 1), 36)
    out = forecast_next(c, Tariff(), date(2026, 11, 5), peak_wp=4000, count=3)
    assert [m["mes"] for m in out] == ["2026-12", "2027-01", "2027-02"]
    assert all(m["fuente"] == "modelo" for m in out)
    # December has less sun than October/November, so more is imported.
    assert out[0]["importada_kwh"] > 5 * 31
    assert out[0]["total"] > 0


def test_forecast_uses_last_year_when_available():
    c = Counters(billing_day=1)
    _history(c, date(2025, 11, 25), 40)  # covers December 2025
    out = forecast_next(c, Tariff(), date(2026, 11, 5), peak_wp=4000, count=1)
    assert out[0]["fuente"] == "año_anterior"
    assert out[0]["importada_kwh"] == pytest.approx(5 * 31)


def test_simulator():
    c = Counters(billing_day=1)
    _history(c, date(2026, 10, 1), 36)
    sim = simulate(c, Tariff(), date(2026, 11, 5), 4000, Scenario(kw_p1=3.45, kw_p2=3.45))
    assert sim["diferencia"] < 0
    more_panels = simulate(c, Tariff(), date(2026, 11, 5), 4000, Scenario(extra_wp=2000))
    assert more_panels["simulada"]["importada_kwh"] <= more_panels["base"]["importada_kwh"]
