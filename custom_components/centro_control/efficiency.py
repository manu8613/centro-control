"""Real efficiency of each PV string against its datasheet (pure Python).

For every string the integration knows the instantaneous DC power, the
irradiance on the plane of the panels (from a sensor or from Open-Meteo) and
the outdoor temperature. With the datasheet values it estimates the cell
temperature and the power the string *should* give right now:

* ``T_cell = T_amb + (NOCT - 20) / 800 * G``  (NOCT model)
* ``P_exp  = Wp * G / 1000 * (1 + γ/100 * (T_cell - 25)) * (1 - degradation/100)``

and reports:

* **rendimiento** (performance index): ``P_real / P_exp`` in %. 100 % means the
  string gives exactly what the datasheet promises for this light and
  temperature; dirt, shade, mismatch, wiring losses or a failing panel lower it.
* **eficiencia de conversión**: ``P_real / (G * area)`` in %, the figure to
  compare with the "module efficiency" of the datasheet (it already includes
  the loss due to temperature). Area = Wp / (1000 W/m² * η_STC).

Instantaneous values are only computed with enough light (``MIN_G_NOW``),
because at low irradiance any error of the irradiance model is huge in
relative terms. The day/month/year figures are energy-weighted
(``Σ E_real / Σ E_exp``) and skip moments in which the inverter is probably
curtailing the panels (battery full and no export).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

MIN_G_NOW = 200.0  # W/m², instantaneous figures
MIN_G_DAY = 100.0  # W/m², accumulated figures
MAX_INDEX = 150.0  # % above which the reading is surely wrong (irradiance model miss)

DEFAULT_GAMMA = -0.30  # %/°C, typical crystalline module
DEFAULT_NOCT = 45.0  # °C
DEFAULT_MODULE_EFF = 21.0  # %


@dataclass(frozen=True)
class StringSpec:
    """Datasheet and mounting of one string."""

    wp: float
    tilt: float | None = None  # ° from horizontal
    azimuth: float | None = None  # ° compass: 0 N, 90 E, 180 S, 270 W
    gamma: float = DEFAULT_GAMMA  # %/°C of Pmax
    noct: float = DEFAULT_NOCT  # °C
    module_eff: float = DEFAULT_MODULE_EFF  # % at STC
    degradation: float = 0.0  # % already lost by age

    @property
    def area_m2(self) -> float:
        return self.wp / (10.0 * self.module_eff) if self.module_eff > 0 else 0.0

    @property
    def plane(self) -> tuple[float, float] | None:
        """(tilt, azimuth in Open-Meteo convention: 0 S, -90 E, 90 W)."""
        if self.tilt is None or self.azimuth is None:
            return None
        return (round(float(self.tilt), 1), round(open_meteo_azimuth(self.azimuth), 1))


def open_meteo_azimuth(compass: float) -> float:
    """Compass azimuth (0 N, 90 E, 180 S, 270 W) → Open-Meteo (0 S, -90 E, 90 W, ±180 N)."""
    value = (float(compass) - 180.0) % 360.0
    return value - 360.0 if value > 180.0 else value


def cell_temperature(t_amb: float, g: float, noct: float) -> float:
    return t_amb + (noct - 20.0) / 800.0 * max(g, 0.0)


def expected_power(spec: StringSpec, g: float, t_cell: float) -> float:
    factor = 1.0 + spec.gamma / 100.0 * (t_cell - 25.0)
    return max(spec.wp * max(g, 0.0) / 1000.0 * factor * (1.0 - spec.degradation / 100.0), 0.0)


def evaluate(spec: StringSpec, power_w: float | None, g: float | None, t_amb: float | None) -> dict[str, Any]:
    """Figures for one string right now. Missing data gives ``None`` values and an ``estado``."""
    out: dict[str, Any] = {
        "irradiancia_wm2": None if g is None else round(g, 0),
        "t_ambiente": None if t_amb is None else round(t_amb, 1),
        "t_celda": None,
        "p_esperada_w": None,
        "rendimiento_pct": None,
        "eficiencia_pct": None,
        "perdida_temp_pct": None,
        "estado": "",
    }
    if not spec.wp:
        out["estado"] = "falta la potencia pico"
        return out
    if g is None:
        out["estado"] = "sin irradiancia"
        return out
    if t_amb is None:
        out["estado"] = "sin temperatura exterior"
        return out
    t_cell = cell_temperature(t_amb, g, spec.noct)
    p_exp = expected_power(spec, g, t_cell)
    out["t_celda"] = round(t_cell, 1)
    out["p_esperada_w"] = round(p_exp, 0)
    out["perdida_temp_pct"] = round(-spec.gamma * (t_cell - 25.0), 1)
    if power_w is None:
        out["estado"] = "sin potencia del string"
        return out
    if g < MIN_G_NOW:
        out["estado"] = "poca luz"
        return out
    index = 100.0 * power_w / p_exp if p_exp > 0 else None
    if index is None or index > MAX_INDEX:
        out["estado"] = "irradiancia poco fiable"
        return out
    out["rendimiento_pct"] = round(index, 1)
    if spec.area_m2:
        out["eficiencia_pct"] = round(100.0 * power_w / (g * spec.area_m2), 2)
    out["estado"] = "ok"
    return out


def counts_for_day(g: float | None, power_w: float | None, p_exp: float | None, curtailed: bool) -> bool:
    """Whether this sample is added to the energy-weighted day/month figures."""
    return bool(
        g is not None and g >= MIN_G_DAY and power_w is not None and p_exp and not curtailed and 100.0 * power_w / p_exp <= MAX_INDEX
    )


def ratio(real_kwh: float, expected_kwh: float) -> float | None:
    return round(100.0 * real_kwh / expected_kwh, 1) if expected_kwh > 0.05 else None


# --------------------------------------------------------------------- Open-Meteo


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def open_meteo_params(lat: float, lon: float, plane: tuple[float, float]) -> dict[str, str]:
    tilt, azimuth = plane
    return {
        "latitude": f"{lat:.4f}",
        "longitude": f"{lon:.4f}",
        "minutely_15": "global_tilted_irradiance_instant,temperature_2m",
        "tilt": f"{tilt:g}",
        "azimuth": f"{azimuth:g}",
        "past_minutely_15": "2",
        "forecast_minutely_15": "4",
        "timeformat": "unixtime",
        "timezone": "GMT",
    }


def parse_open_meteo(payload: dict[str, Any]) -> list[tuple[float, float | None, float | None]]:
    """``[(timestamp, gti, temperature), …]`` from a ``minutely_15`` response."""
    block = payload.get("minutely_15") or {}
    times = block.get("time") or []
    gti = block.get("global_tilted_irradiance_instant") or []
    temp = block.get("temperature_2m") or []
    rows = []
    for i, ts in enumerate(times):
        g = gti[i] if i < len(gti) else None
        t = temp[i] if i < len(temp) else None
        rows.append((float(ts), None if g is None else float(g), None if t is None else float(t)))
    return rows


def interpolate(rows: list[tuple[float, float | None, float | None]], ts: float) -> tuple[float | None, float | None]:
    """Irradiance and temperature at ``ts`` (linear between the two 15-min points around it)."""
    rows = sorted(r for r in rows if r[1] is not None)
    if not rows or ts < rows[0][0] - 900 or ts > rows[-1][0] + 900:
        return None, None
    before = [r for r in rows if r[0] <= ts]
    after = [r for r in rows if r[0] >= ts]
    a = before[-1] if before else after[0]
    b = after[0] if after else before[-1]
    if b[0] == a[0]:
        return a[1], a[2]
    k = (ts - a[0]) / (b[0] - a[0])

    def mix(x: float | None, y: float | None) -> float | None:
        if x is None or y is None:
            return x if y is None else y
        return x + (y - x) * k

    g = mix(a[1], b[1])
    return (None if g is None or math.isnan(g) else max(g, 0.0)), mix(a[2], b[2])
