"""Measured irradiance from a SiAR agroclimatic station (pure Python).

SiAR (Sistema de Información Agroclimática para el Regadío, Spanish Ministry
of Agriculture) publishes half-hourly records of its stations: mean global
*horizontal* irradiance (``Radiacion``, W/m²) and mean air temperature
(``TempMedia``, °C). Its Web API needs a token obtained with the user and
password of the ministry's REGEUS account (API access requested in "Mi SiAR").

What this module does:

* parse the ``Datos/Horarios/ESTACION`` answer into half-hour slots;
* find out whether the station's clock is UTC or local time (the API manual
  does not say) by comparing the centre of mass of the day's irradiance with
  solar noon;
* move the horizontal irradiance to the plane of each string (Erbs diffuse
  fraction + Hay-Davies transposition), so it can be compared with the power
  the string gave in the same half hour.

The station is some kilometres away and gives 30-minute means, so SiAR is used
for the *measured* figures per half hour and per day, not for the
instantaneous value (Open-Meteo or an own sensor keep doing that).
"""

from __future__ import annotations

import math
import re
from datetime import UTC, date, datetime, timedelta
from statistics import median
from typing import Any

SIAR_URL = "https://servicio.mapa.gob.es/siarapi/API/V1"
SLOT = 1800  # s, SiAR records are half-hourly means
INVALID = -999.0  # SiAR uses -6999 / -99999 for datalogger failures
ALBEDO = 0.2
MIN_ELEVATION = 5.0  # °, below this the transposition is meaningless
MIN_COVERAGE = 0.8  # part of the half hour with power samples
SOLAR_CONSTANT = 1367.0


# --------------------------------------------------------------------- API answers


def text_of(payload: Any) -> str:
    """The string inside an API answer (plain JSON string, or the first string value of an object)."""
    if isinstance(payload, str):
        return payload.strip().strip('"')
    if isinstance(payload, dict):
        for key in ("token", "Token", "cadena", "Cadena", "Datos", "datos", "resultado", "Resultado"):
            if isinstance(payload.get(key), str):
                return payload[key].strip()
        for value in payload.values():
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def _records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        if payload and all(isinstance(r, dict) for r in payload) and any("HorMin" in r or "horMin" in r for r in payload):
            return payload
        for item in payload:
            found = _records(item)
            if found:
                return found
    elif isinstance(payload, dict):
        for value in payload.values():
            found = _records(value)
            if found:
                return found
    return []


def _day(value: Any) -> date | None:
    text = str(value or "").strip()
    if m := re.match(r"(\d{4})-(\d{2})-(\d{2})", text):
        return date(int(m[1]), int(m[2]), int(m[3]))
    if m := re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", text):
        return date(int(m[3]), int(m[2]), int(m[1]))
    return None


def _num(value: Any) -> float | None:
    try:
        number = float(str(value).replace(",", ".")) if value not in (None, "") else None
    except ValueError:
        return None
    return None if number is None or number <= INVALID or math.isnan(number) else number


def parse_rows(payload: Any) -> list[tuple[date, int, float | None, float | None]]:
    """``[(date, HHMM end of the half hour, GHI W/m², air °C), …]``."""
    rows = []
    for r in _records(payload):
        get = {k.lower(): v for k, v in r.items()}.get
        day = _day(get("fecha"))
        try:
            hhmm = int(float(get("hormin")))
        except (TypeError, ValueError):
            continue
        if day is None or not 0 <= hhmm <= 2400:
            continue
        rows.append((day, hhmm, _num(get("radiacion")), _num(get("tempmedia"))))
    return sorted(rows)


def slot_start(day: date, hhmm: int, offset_h: int) -> float:
    """UTC timestamp of the start of the half hour that ends at ``hhmm`` (station clock = UTC + offset)."""
    end = datetime(day.year, day.month, day.day, tzinfo=UTC) + timedelta(hours=hhmm // 100, minutes=hhmm % 100)
    return (end - timedelta(hours=offset_h)).timestamp() - SLOT


# --------------------------------------------------------------------- sun


def _sun_terms(ts: float) -> tuple[float, float, int]:
    """(declination rad, equation of time min, day of year)."""
    moment = datetime.fromtimestamp(ts, UTC)
    doy = moment.timetuple().tm_yday
    hour = moment.hour + moment.minute / 60 + moment.second / 3600
    g = 2 * math.pi / 365 * (doy - 1 + (hour - 12) / 24)
    eot = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g) - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    decl = (
        0.006918
        - 0.399912 * math.cos(g)
        + 0.070257 * math.sin(g)
        - 0.006758 * math.cos(2 * g)
        + 0.000907 * math.sin(2 * g)
        - 0.002697 * math.cos(3 * g)
        + 0.00148 * math.sin(3 * g)
    )
    return decl, eot, doy


def sun_position(ts: float, lat: float, lon: float) -> tuple[float, float]:
    """(elevation °, azimuth ° compass: 0 N, 90 E, 180 S)."""
    decl, eot, _ = _sun_terms(ts)
    moment = datetime.fromtimestamp(ts, UTC)
    minutes = moment.hour * 60 + moment.minute + moment.second / 60
    hour_angle = math.radians((minutes + eot + 4 * lon) / 4 - 180)
    phi = math.radians(lat)
    cos_z = math.sin(phi) * math.sin(decl) + math.cos(phi) * math.cos(decl) * math.cos(hour_angle)
    cos_z = max(-1.0, min(1.0, cos_z))
    zenith = math.acos(cos_z)
    elevation = 90 - math.degrees(zenith)
    if math.sin(zenith) < 1e-6:
        return elevation, 180.0
    cos_az = (math.sin(decl) - math.sin(phi) * cos_z) / (math.cos(phi) * math.sin(zenith))
    azimuth = math.degrees(math.acos(max(-1.0, min(1.0, cos_az))))
    return elevation, (azimuth if hour_angle < 0 else 360 - azimuth)


def solar_noon_utc_h(day: date, lon: float) -> float:
    ts = datetime(day.year, day.month, day.day, 12, tzinfo=UTC).timestamp()
    _, eot, _ = _sun_terms(ts)
    return 12 - lon / 15 - eot / 60


def detect_offset(rows: list[tuple[date, int, float | None, float | None]], lon: float) -> int | None:
    """Hours between the station clock and UTC (0, 1 or 2), from the irradiance of each full day."""
    by_day: dict[date, list[tuple[float, float]]] = {}
    for day, hhmm, ghi, _ in rows:
        if ghi is not None and ghi > 5:
            by_day.setdefault(day, []).append((hhmm // 100 + hhmm % 100 / 60 - 0.25, ghi))
    found = []
    for day, items in by_day.items():
        total = sum(g for _, g in items)
        if len(items) < 8 or total < 500:
            continue
        centre = sum(h * g for h, g in items) / total
        found.append(centre - solar_noon_utc_h(day, lon))
    if not found:
        return None
    return max(0, min(2, round(median(found))))


# --------------------------------------------------------------------- transposition


def plane_irradiance(ghi: float, ts: float, lat: float, lon: float, tilt: float, azimuth: float) -> float | None:
    """Global horizontal → plane of array (W/m²). ``None`` with the sun too low."""
    elevation, sun_az = sun_position(ts, lat, lon)
    if elevation < MIN_ELEVATION or ghi <= 0:
        return None
    _, _, doy = _sun_terms(ts)
    cos_z = math.sin(math.radians(elevation))
    i0 = SOLAR_CONSTANT * (1 + 0.033 * math.cos(2 * math.pi * doy / 365))
    kt = min(max(ghi / (i0 * cos_z), 0.0), 1.0)
    if kt <= 0.22:  # Erbs
        fd = 1 - 0.09 * kt
    elif kt <= 0.80:
        fd = 0.9511 - 0.1604 * kt + 4.388 * kt**2 - 16.638 * kt**3 + 12.336 * kt**4
    else:
        fd = 0.165
    dhi = ghi * fd
    dni = min((ghi - dhi) / cos_z, 1100.0)
    b, s = math.radians(tilt), math.radians(90 - elevation)
    cos_aoi = math.cos(s) * math.cos(b) + math.sin(s) * math.sin(b) * math.cos(math.radians(sun_az - azimuth))
    cos_aoi = max(cos_aoi, 0.0)
    ai = dni / i0  # Hay-Davies anisotropy index
    diffuse = dhi * (ai * cos_aoi / cos_z + (1 - ai) * (1 + math.cos(b)) / 2)
    ground = ghi * ALBEDO * (1 - math.cos(b)) / 2
    return max(dni * cos_aoi + diffuse + ground, 0.0)


# --------------------------------------------------------------------- power samples per half hour


def slot_of(ts: float) -> int:
    return int(ts // SLOT * SLOT)


def add_sample(slots: dict[int, list[float]], ts: float, dt: float, watts: float, temp: float | None, curtailed: bool) -> None:
    """Accumulate one power sample: ``[Σ W·s, Σ s, Σ °C·s, Σ s with °C, curtailed]``."""
    slot = slots.setdefault(slot_of(ts), [0.0, 0.0, 0.0, 0.0, 0.0])
    slot[0] += watts * dt
    slot[1] += dt
    if temp is not None:
        slot[2] += temp * dt
        slot[3] += dt
    if curtailed:
        slot[4] = 1.0


def slot_means(slot: list[float]) -> tuple[float | None, float | None, bool]:
    """(mean W, mean °C, usable) of one accumulated half hour."""
    watts = slot[0] / slot[1] if slot[1] else None
    temp = slot[2] / slot[3] if slot[3] else None
    return watts, temp, slot[1] >= MIN_COVERAGE * SLOT and not slot[4]
