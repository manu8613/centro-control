"""Real efficiency of the PV strings against the datasheet."""

from __future__ import annotations

import pytest

from custom_components.centro_control.efficiency import (
    MIN_G_NOW,
    StringSpec,
    cell_temperature,
    counts_for_day,
    evaluate,
    expected_power,
    interpolate,
    open_meteo_azimuth,
    open_meteo_params,
    parse_open_meteo,
    ratio,
)

# A 595 Wp module: γ -0.26 %/°C, η 23.0 %, NOCT derived from the datasheet (448 W at 800 W/m², 20 °C)
SPEC = StringSpec(wp=9 * 595, tilt=30, azimuth=180, gamma=-0.26, noct=47.6, module_eff=23.0)


def test_cell_temperature_and_expected_power():
    t = cell_temperature(10, 800, 47.6)
    assert t == pytest.approx(37.6)
    assert expected_power(SPEC, 800, t) == pytest.approx(5355 * 0.8 * (1 - 0.0026 * 12.6), rel=1e-6)
    assert expected_power(SPEC, 1000, 25) == pytest.approx(5355)
    assert expected_power(StringSpec(wp=1000, degradation=2), 1000, 25) == pytest.approx(980)


def test_noct_of_the_datasheet_gives_its_noct_power():
    one = StringSpec(wp=595, gamma=-0.26, noct=47.6)
    assert expected_power(one, 800, cell_temperature(20, 800, 47.6)) == pytest.approx(448, rel=0.01)


def test_evaluate_ok_and_conversion_efficiency():
    data = evaluate(SPEC, 3900, 800, 10)
    assert data["estado"] == "ok"
    assert data["rendimiento_pct"] == pytest.approx(100 * 3900 / data["p_esperada_w"], abs=0.1)
    # area = 5355 / 230 = 23.28 m²  → 3900 / (800 * 23.28) = 20.9 %
    assert data["eficiencia_pct"] == pytest.approx(20.94, abs=0.05)
    assert data["perdida_temp_pct"] == pytest.approx(3.3, abs=0.1)


@pytest.mark.parametrize(
    ("power", "g", "t", "estado"),
    [
        (100, MIN_G_NOW - 1, 10, "poca luz"),
        (100, None, 10, "sin irradiancia"),
        (100, 800, None, "sin temperatura exterior"),
        (None, 800, 10, "sin potencia del string"),
        (9000, 500, 10, "irradiancia poco fiable"),
    ],
)
def test_evaluate_without_good_data(power, g, t, estado):
    data = evaluate(SPEC, power, g, t)
    assert data["estado"] == estado
    assert data["rendimiento_pct"] is None


def test_day_samples_and_ratio():
    assert counts_for_day(500, 2000, 2200, False)
    assert not counts_for_day(500, 2000, 2200, True)  # curtailed by the inverter
    assert not counts_for_day(50, 200, 220, False)
    assert ratio(9, 10) == 90
    assert ratio(0.01, 0.02) is None


@pytest.mark.parametrize(("compass", "om"), [(180, 0), (90, -90), (270, 90), (0, 180), (135, -45), (225, 45)])
def test_azimuth_conversion(compass, om):
    assert open_meteo_azimuth(compass) == om


def test_open_meteo_parse_and_interpolate():
    params = open_meteo_params(42.01, -4.53, SPEC.plane)
    assert params["tilt"] == "30" and params["azimuth"] == "0"
    rows = parse_open_meteo({"minutely_15": {"time": [0, 900, 1800], "global_tilted_irradiance_instant": [400, 600, None], "temperature_2m": [10, 12, 13]}})
    assert interpolate(rows, 450) == (500, 11)
    assert interpolate(rows, 900) == (600, 12)
    assert interpolate(rows, 1000) == (600, 12)
    assert interpolate(rows, 10_000) == (None, None)
    assert interpolate([], 0) == (None, None)
