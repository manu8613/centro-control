"""Cloud cover -> expected solar energy -> advice on charging the battery from the grid.

Pure functions (no Home Assistant imports) so they can be tested on their own.

The battery should be used from 08:00 to 00:00, so the night (00:00-08:00) is
the window to top it up from the grid when the next day is not going to be
sunny enough. The advice is a heuristic: it needs the installed peak power,
the usable battery capacity, the current SOC and the usual daily consumption.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import math
from typing import Any

DAY_START_H = 8  # the battery is meant to be used from 08:00...
DAY_END_H = 24  # ...until midnight
SOLAR_END_H = 17  # rough end of useful solar production (winter-biased: conservative)
EFFICIENCY = 0.90  # solar -> load/battery round trip
MARGIN = 0.10  # extra energy over the estimated need
PR = 0.80  # performance ratio of the installation
CLEARNESS = 0.72  # clear-sky fraction of the extraterrestrial irradiation
TOLERANCE_PCT = 5  # do not bother charging for a shortfall smaller than this

# Home Assistant weather conditions -> typical cloud cover (%), used when the
# forecast has no cloud_coverage.
CONDITION_CLOUD: dict[str, float] = {
    "sunny": 5,
    "clear-night": 5,
    "windy": 30,
    "partlycloudy": 45,
    "windy-variant": 60,
    "cloudy": 85,
    "fog": 90,
    "rainy": 95,
    "lightning": 95,
    "snowy": 95,
    "hail": 100,
    "pouring": 100,
    "lightning-rainy": 100,
    "snowy-rainy": 100,
}


def _es(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


def _num(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def clear_sky_kwh_per_kwp(latitude: float, day_of_year: int) -> float:
    """Daily energy (kWh) of 1 kWp on a clear day, for a typical tilted roof.

    Extraterrestrial irradiation from latitude and date, times the clear-sky
    fraction, a seasonal tilt gain and the performance ratio.
    """
    phi = math.radians(max(-66.0, min(66.0, latitude)))
    delta = math.radians(23.45) * math.sin(2 * math.pi * (284 + day_of_year) / 365)
    cos_ws = max(-1.0, min(1.0, -math.tan(phi) * math.tan(delta)))
    ws = math.acos(cos_ws)
    e0 = 1 + 0.033 * math.cos(2 * math.pi * day_of_year / 365)
    h0 = 24 / math.pi * 1.367 * e0 * (math.cos(phi) * math.cos(delta) * math.sin(ws) + ws * math.sin(phi) * math.sin(delta))
    hemisphere = 1 if latitude >= 0 else -1
    tilt_gain = 1.05 - 0.17 * hemisphere * math.sin(delta) / math.sin(math.radians(23.45))
    return max(h0, 0.0) * CLEARNESS * tilt_gain * PR


def cloud_factor(cloud_pct: float) -> float:
    """Share of the clear-sky production that is left under ``cloud_pct`` % of clouds."""
    c = max(0.0, min(100.0, cloud_pct)) / 100
    return 1 - 0.85 * c**2.5


def expected_solar_kwh(peak_wp: float, latitude: float, day: date, cloud_pct: float) -> float:
    return (peak_wp / 1000) * clear_sky_kwh_per_kwp(latitude, day.timetuple().tm_yday) * cloud_factor(cloud_pct)


def cloud_from(entry: dict[str, Any]) -> tuple[float | None, str]:
    """Cloud cover of one forecast entry: (percent, origin)."""
    cover = _num(entry.get("cloud_coverage"))
    if cover is not None:
        return max(0.0, min(100.0, cover)), "pronostico"
    mapped = CONDITION_CLOUD.get(str(entry.get("condition", "")))
    if mapped is not None:
        return mapped, "estimada"
    return None, ""


def normalize_forecast(raw: list[dict[str, Any]] | None, current: dict[str, Any] | None = None, today: date | None = None) -> list[dict[str, Any]]:
    """Daily forecast -> ``[{fecha, nubes_pct, origen, condicion}]`` (one per date, ascending).

    ``current`` (the weather entity's attributes + state) fills in today when the
    forecast does not include it.
    """
    days: dict[str, dict[str, Any]] = {}
    for entry in raw or []:
        stamp = str(entry.get("datetime", ""))[:10]
        if len(stamp) != 10:
            continue
        pct, origin = cloud_from(entry)
        if stamp not in days:
            days[stamp] = {"fecha": stamp, "nubes_pct": pct, "origen": origin, "condicion": entry.get("condition")}
    if today is not None and current and today.isoformat() not in days:
        pct, origin = cloud_from(current)
        if pct is not None:
            days[today.isoformat()] = {"fecha": today.isoformat(), "nubes_pct": pct, "origen": origin, "condicion": current.get("condition")}
    out = sorted(days.values(), key=lambda d: d["fecha"])
    if today is not None:
        out = [d for d in out if d["fecha"] >= today.isoformat()]
    return out[:6]


@dataclass
class Advice:
    estado: str  # "cargar" | "no_cargar" | "sin_datos"
    soc_objetivo: int | None = None
    soc_previsto: float | None = None  # SOC expected at 08:00 if the grid does not charge
    deficit_kwh: float = 0.0
    motivo: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "estado": self.estado,
            "soc_objetivo": self.soc_objetivo,
            "soc_previsto_08h": None if self.soc_previsto is None else round(self.soc_previsto, 1),
            "deficit_kwh": round(self.deficit_kwh, 1),
            "motivo": self.motivo,
        }


def advise(
    *,
    now: datetime,
    soc_now: float | None,
    capacity_kwh: float,
    reserve_pct: float,
    daily_load_kwh: float | None,
    day_share_pct: float,
    solar_target_kwh: float | None,
    solar_today_kwh: float | None,
    cloud_target_pct: float | None = None,
) -> Advice:
    """Should the battery be charged from the grid tonight?

    ``solar_target_kwh`` is the production expected on the day to cover: today
    when it is before 08:00, tomorrow otherwise. ``solar_today_kwh`` is used to
    estimate how much more the sun will give before sunset (daytime only).
    """
    if soc_now is None or capacity_kwh <= 0 or not daily_load_kwh or daily_load_kwh <= 0 or solar_target_kwh is None:
        return Advice("sin_datos", motivo="Faltan datos: SOC de la batería, capacidad, consumo medio o previsión del cielo.")

    hour = now.hour + now.minute / 60
    share = max(0.3, min(1.0, day_share_pct / 100))
    load_day = daily_load_kwh * share  # 08:00-00:00
    load_night = daily_load_kwh - load_day  # 00:00-08:00
    reserve_kwh = capacity_kwh * max(0.0, min(90.0, reserve_pct)) / 100
    energy = capacity_kwh * max(0.0, min(100.0, soc_now)) / 100

    if hour >= DAY_START_H:  # project to midnight, then through the night
        remaining_load = load_day * (DAY_END_H - hour) / (DAY_END_H - DAY_START_H)
        remaining_solar = (solar_today_kwh or 0.0) * max(0.0, min(1.0, (SOLAR_END_H - hour) / (SOLAR_END_H - DAY_START_H))) * EFFICIENCY
        energy = max(reserve_kwh, min(capacity_kwh, energy + remaining_solar - remaining_load))
        night_used = load_night
    else:
        night_used = load_night * (DAY_START_H - hour) / DAY_START_H
    energy_08 = max(0.0, energy - night_used)
    soc_08 = 100 * energy_08 / capacity_kwh

    need = max(0.0, load_day * (1 + MARGIN) - solar_target_kwh * EFFICIENCY)  # energy the battery must give 08:00-00:00
    target = min(100.0, reserve_pct + 100 * need / capacity_kwh)
    target = min(100, int(math.ceil(target / 5) * 5))
    deficit = max(0.0, (target - soc_08) / 100 * capacity_kwh)
    day_word = "Hoy" if hour < DAY_START_H else "Mañana"
    cloud = "" if cloud_target_pct is None else f" con un {cloud_target_pct:.0f} % de nubes"
    facts = f"{day_word} se esperan ≈ {_es(solar_target_kwh)} kWh solares{cloud} y de 08:00 a 00:00 gastas ≈ {_es(load_day)} kWh."
    if soc_08 < target - TOLERANCE_PCT:
        return Advice(
            "cargar",
            target,
            soc_08,
            deficit,
            f"{facts} Sin red la batería llegaría a las 08:00 al {soc_08:.0f} % y hace falta el {target} %: conviene cargar ≈ {_es(deficit)} kWh por la red esta noche.",
        )
    return Advice(
        "no_cargar",
        target,
        soc_08,
        0.0,
        f"{facts} La batería llegará a las 08:00 al {soc_08:.0f} % (necesitas el {target} %): no hace falta cargar por la red.",
    )


def daily_load_from_history(history: dict[str, dict[str, float]], today: date, days: int = 7) -> float | None:
    """Average of the last ``days`` complete days with consumption recorded."""
    values = []
    for offset in range(1, days + 1):
        value = history.get(date.fromordinal(today.toordinal() - offset).isoformat(), {}).get("consumo")
        if value and value > 0.5:
            values.append(value)
    return sum(values) / len(values) if values else None


def build_plan(
    *,
    now: datetime,
    latitude: float,
    peak_wp: float,
    capacity_kwh: float,
    soc_now: float | None,
    reserve_pct: float,
    daily_load_kwh: float | None,
    day_share_pct: float,
    forecast: list[dict[str, Any]],
    solar_override: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Everything the sensor/panel shows: cloud cover per day, solar estimate and the advice."""
    override = solar_override or {}
    today = now.date()
    days: list[dict[str, Any]] = []
    for item in forecast:
        day = date.fromisoformat(item["fecha"])
        pct = item.get("nubes_pct")
        if item["fecha"] in override:
            solar, source = override[item["fecha"]], "sensor"
        elif pct is not None and peak_wp > 0:
            solar, source = expected_solar_kwh(peak_wp, latitude, day, pct), "estimacion"
        else:
            solar, source = None, ""
        coverage = round(100 * solar / daily_load_kwh) if solar is not None and daily_load_kwh else None
        days.append(
            {
                "fecha": item["fecha"],
                "nubes_pct": None if pct is None else round(pct),
                "origen_nubes": item.get("origen", ""),
                "condicion": item.get("condicion"),
                "solar_kwh": None if solar is None else round(solar, 1),
                "origen_solar": source,
                "cobertura_pct": coverage,
            }
        )
    by_date = {d["fecha"]: d for d in days}
    target_date = today if now.hour < DAY_START_H else date.fromordinal(today.toordinal() + 1)
    target = by_date.get(target_date.isoformat())
    today_entry = by_date.get(today.isoformat())
    advice = advise(
        now=now,
        soc_now=soc_now,
        capacity_kwh=capacity_kwh,
        reserve_pct=reserve_pct,
        daily_load_kwh=daily_load_kwh,
        day_share_pct=day_share_pct,
        solar_target_kwh=None if target is None else target["solar_kwh"],
        solar_today_kwh=None if today_entry is None else today_entry["solar_kwh"],
        cloud_target_pct=None if target is None else target["nubes_pct"],
    )
    return {
        **advice.as_dict(),
        "dia_objetivo": target_date.isoformat(),
        "consumo_diario_kwh": None if daily_load_kwh is None else round(daily_load_kwh, 1),
        "capacidad_kwh": capacity_kwh,
        "dias": days,
    }
