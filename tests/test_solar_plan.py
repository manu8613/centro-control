"""Cloud cover -> solar estimate -> night grid-charge advice."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from custom_components.centro_control.solar_plan import (
    advise,
    build_plan,
    clear_sky_kwh_per_kwp,
    cloud_factor,
    cloud_from,
    daily_load_from_history,
    expected_solar_kwh,
    normalize_forecast,
)


def test_clear_sky_is_higher_in_summer_and_sane():
    winter = clear_sky_kwh_per_kwp(42.0, 314)  # 10 Nov
    summer = clear_sky_kwh_per_kwp(42.0, 172)  # 21 Jun
    assert 2.5 < winter < 4.0
    assert 5.0 < summer < 7.5
    assert summer > winter


def test_clear_sky_polar_night_does_not_crash():
    assert clear_sky_kwh_per_kwp(66.0, 355) >= 0


def test_cloud_factor_is_monotonic_and_bounded():
    values = [cloud_factor(c) for c in range(0, 101, 10)]
    assert values[0] == 1
    assert values == sorted(values, reverse=True)
    assert 0.1 < values[-1] < 0.3
    assert cloud_factor(-20) == 1
    assert cloud_factor(500) == values[-1]


def test_expected_solar_scales_with_peak_and_clouds():
    day = date(2026, 11, 10)
    clear = expected_solar_kwh(5000, 42.0, day, 0)
    assert expected_solar_kwh(10000, 42.0, day, 0) == pytest.approx(2 * clear)
    assert expected_solar_kwh(5000, 42.0, day, 100) < clear / 3


def test_cloud_from_prefers_coverage_then_condition():
    assert cloud_from({"cloud_coverage": 73, "condition": "sunny"}) == (73.0, "pronostico")
    assert cloud_from({"condition": "cloudy"}) == (85, "estimada")
    assert cloud_from({"condition": "exceptional"}) == (None, "")
    assert cloud_from({"cloud_coverage": "abc"}) == (None, "")


def test_normalize_forecast_orders_dedupes_and_fills_today():
    raw = [
        {"datetime": "2026-11-12T00:00:00+00:00", "cloud_coverage": 80},
        {"datetime": "2026-11-11T00:00:00+00:00", "condition": "rainy"},
        {"datetime": "2026-11-11T12:00:00+00:00", "cloud_coverage": 10},
        {"datetime": "mal"},
    ]
    out = normalize_forecast(raw, {"condition": "partlycloudy"}, date(2026, 11, 10))
    assert [d["fecha"] for d in out] == ["2026-11-10", "2026-11-11", "2026-11-12"]
    assert out[0]["nubes_pct"] == 45 and out[0]["origen"] == "estimada"
    assert out[1]["nubes_pct"] == 52.5  # entries of the same day are averaged (95 and 10)
    assert out[2]["origen"] == "pronostico"


def test_normalize_forecast_uses_the_local_day():
    from zoneinfo import ZoneInfo

    # Met.no style: local midnight of the 11th arrives as 23:00 UTC of the 10th
    raw = [{"datetime": "2026-11-10T23:00:00+00:00", "cloud_coverage": 30}, {"datetime": "2026-11-11T23:00:00+00:00", "cloud_coverage": 60}]
    out = normalize_forecast(raw, None, date(2026, 11, 11), ZoneInfo("Europe/Madrid"))
    assert [(d["fecha"], d["nubes_pct"]) for d in out] == [("2026-11-11", 30), ("2026-11-12", 60)]


def test_normalize_forecast_averages_hourly_entries():
    raw = [{"datetime": f"2026-11-10T{h:02d}:00:00+01:00", "cloud_coverage": 20 if h < 12 else 60} for h in range(24)]
    out = normalize_forecast(raw, None, date(2026, 11, 10))
    assert len(out) == 1 and out[0]["nubes_pct"] == 40 and out[0]["origen"] == "pronostico"


def test_normalize_forecast_drops_past_and_caps_at_six_days():
    raw = [{"datetime": f"2026-11-{d:02d}T00:00:00", "cloud_coverage": 50} for d in range(1, 20)]
    out = normalize_forecast(raw, None, date(2026, 11, 10))
    assert out[0]["fecha"] == "2026-11-10" and len(out) == 6


def _advise(**kw):
    base = dict(
        now=datetime(2026, 11, 10, 22, 0),
        soc_now=30.0,
        capacity_kwh=32.0,
        reserve_pct=10.0,
        daily_load_kwh=14.0,
        day_share_pct=85.0,
        solar_target_kwh=3.0,
        solar_today_kwh=3.0,
        cloud_target_pct=90.0,
    )
    base.update(kw)
    return advise(**base)


def test_dull_day_after_a_low_battery_asks_for_grid_charge():
    advice = _advise()
    assert advice.estado == "cargar"
    assert advice.soc_objetivo is not None and advice.soc_objetivo > 30
    assert advice.deficit_kwh > 0
    assert "90 % de nubes" in advice.motivo


def test_sunny_day_and_full_battery_needs_no_grid():
    advice = _advise(soc_now=95.0, solar_target_kwh=14.0, cloud_target_pct=5.0)
    assert advice.estado == "no_cargar"
    assert advice.deficit_kwh == 0


def test_target_never_exceeds_100_and_is_a_multiple_of_five():
    advice = _advise(daily_load_kwh=60.0, solar_target_kwh=0.5)
    assert advice.soc_objetivo == 100
    assert _advise().soc_objetivo % 5 == 0


def test_before_eight_the_target_day_is_today_and_no_more_solar_is_counted():
    advice = _advise(now=datetime(2026, 11, 10, 3, 0), soc_now=40.0)
    assert advice.motivo.startswith("Hoy")
    assert advice.soc_previsto is not None and advice.soc_previsto < 40


def test_daytime_projection_counts_remaining_sun_but_never_below_reserve():
    low = _advise(now=datetime(2026, 11, 10, 10, 0), soc_now=12.0, solar_today_kwh=0.0)
    assert low.soc_previsto is not None and low.soc_previsto <= 10.1
    sunny = _advise(now=datetime(2026, 11, 10, 10, 0), soc_now=12.0, solar_today_kwh=20.0)
    assert sunny.soc_previsto > low.soc_previsto


@pytest.mark.parametrize("missing", ["soc_now", "daily_load_kwh", "solar_target_kwh"])
def test_missing_data_gives_sin_datos(missing):
    assert _advise(**{missing: None}).estado == "sin_datos"
    assert _advise(capacity_kwh=0).estado == "sin_datos"


def test_daily_load_from_history_uses_complete_days_only():
    history = {"2026-11-09": {"consumo": 12.0}, "2026-11-08": {"consumo": 16.0}, "2026-11-07": {"consumo": 0.0}, "2026-11-10": {"consumo": 99.0}}
    assert daily_load_from_history(history, date(2026, 11, 10)) == pytest.approx(14.0)
    assert daily_load_from_history({}, date(2026, 11, 10)) is None


def test_build_plan_uses_overrides_and_picks_tomorrow_in_the_evening():
    forecast = [
        {"fecha": "2026-11-10", "nubes_pct": 20.0, "origen": "pronostico", "condicion": "sunny"},
        {"fecha": "2026-11-11", "nubes_pct": 95.0, "origen": "pronostico", "condicion": "rainy"},
        {"fecha": "2026-11-12", "nubes_pct": None, "origen": "", "condicion": None},
    ]
    plan = build_plan(
        now=datetime(2026, 11, 10, 21, 0),
        latitude=42.0,
        peak_wp=6000,
        capacity_kwh=32.0,
        soc_now=35.0,
        reserve_pct=10.0,
        daily_load_kwh=14.0,
        day_share_pct=85.0,
        forecast=forecast,
        solar_override={"2026-11-11": 2.0},
    )
    assert plan["dia_objetivo"] == "2026-11-11"
    assert plan["dias"][1]["solar_kwh"] == 2.0 and plan["dias"][1]["origen_solar"] == "sensor"
    assert plan["dias"][0]["origen_solar"] == "estimacion" and plan["dias"][0]["solar_kwh"] > 5
    assert plan["dias"][2]["solar_kwh"] is None
    assert plan["estado"] == "cargar"
    assert plan["dias"][1]["cobertura_pct"] == round(100 * 2.0 / 14.0)


def test_build_plan_without_forecast_is_sin_datos():
    plan = build_plan(
        now=datetime(2026, 11, 10, 21, 0), latitude=42.0, peak_wp=6000, capacity_kwh=32.0, soc_now=35.0,
        reserve_pct=10.0, daily_load_kwh=14.0, day_share_pct=85.0, forecast=[],
    )
    assert plan["estado"] == "sin_datos" and plan["dias"] == []
