"""SiAR: parsing, station clock, transposition and half-hour samples."""

from __future__ import annotations

import math
from datetime import UTC, date, datetime

import pytest

from custom_components.centro_control.siar import (
    SLOT,
    add_sample,
    detect_offset,
    parse_rows,
    plane_irradiance,
    slot_means,
    slot_of,
    slot_start,
    sun_position,
    text_of,
)

LAT, LON = 42.0, -4.5


def clear_rows(day: date, offset: int) -> list[dict]:
    """A clear day as SiAR would give it, with the station clock at UTC + offset."""
    rows = []
    for i in range(1, 49):
        end = datetime(day.year, day.month, day.day, tzinfo=UTC).timestamp() + i * SLOT
        elevation, _ = sun_position(end - SLOT / 2 - offset * 3600, LAT, LON)
        ghi = max(0.0, 1000 * math.sin(math.radians(elevation)) ** 1.15) if elevation > 0 else 0.0
        rows.append({"Fecha": day.isoformat(), "HorMin": (i * 30 // 60) * 100 + (i * 30) % 60, "Radiacion": round(ghi, 1), "TempMedia": 20})
    return rows


def test_parse_rows_formats_and_failures():
    payload = {
        "Datos": [
            {"Fecha": "2026-06-10T00:00:00", "HorMin": 1230, "Radiacion": 800.5, "TempMedia": "21,5"},
            {"fecha": "10/06/2026", "horMin": "1300", "radiacion": -6999, "tempMedia": 22},
            {"Fecha": "2026-06-10", "HorMin": "x", "Radiacion": 1},
        ]
    }
    rows = parse_rows(payload)
    assert rows == [(date(2026, 6, 10), 1230, 800.5, 21.5), (date(2026, 6, 10), 1300, None, 22.0)]
    assert parse_rows("sin datos") == []
    assert parse_rows([[], {"x": clear_rows(date(2026, 6, 10), 0)[:2]}])[0][1] == 30


def test_text_of():
    assert text_of('"abc"') == "abc"
    assert text_of({"Token": "t0k"}) == "t0k"
    assert text_of({"otro": 1, "valor": "x"}) == "x"
    assert text_of(None) == ""


@pytest.mark.parametrize("offset", [0, 1, 2])
def test_station_clock_is_detected(offset):
    day = date(2026, 6, 10)
    assert detect_offset(parse_rows(clear_rows(day, offset)), LON) == offset


def test_station_clock_needs_a_day_of_light():
    assert detect_offset(parse_rows(clear_rows(date(2026, 6, 10), 0)[:16]), LON) is None


def test_slot_start():
    assert slot_start(date(2026, 6, 10), 1230, 0) == datetime(2026, 6, 10, 12, tzinfo=UTC).timestamp()
    assert slot_start(date(2026, 6, 10), 2400, 2) == datetime(2026, 6, 10, 21, 30, tzinfo=UTC).timestamp()


def test_sun_position_noon():
    noon = datetime(2026, 6, 21, 12, 18, tzinfo=UTC).timestamp()  # solar noon at 4.5° W
    elevation, azimuth = sun_position(noon, LAT, LON)
    assert elevation == pytest.approx(90 - LAT + 23.44, abs=0.5)
    assert azimuth == pytest.approx(180, abs=5)


def test_transposition_is_sane():
    winter_noon = datetime(2026, 12, 21, 12, 18, tzinfo=UTC).timestamp()
    ghi = 500.0
    flat = plane_irradiance(ghi, winter_noon, LAT, LON, 0, 180)
    south = plane_irradiance(ghi, winter_noon, LAT, LON, 35, 180)
    north = plane_irradiance(ghi, winter_noon, LAT, LON, 35, 0)
    assert flat == pytest.approx(ghi, rel=0.01)
    assert south > 1.3 * ghi
    assert north < ghi
    night = datetime(2026, 12, 21, 23, tzinfo=UTC).timestamp()
    assert plane_irradiance(ghi, night, LAT, LON, 35, 180) is None


def test_half_hour_samples():
    slots: dict[int, list[float]] = {}
    start = 1_800_000_000 // SLOT * SLOT
    for i in range(180):  # 30 min of 10 s samples
        add_sample(slots, start + i * 10, 10, 1000, 20 if i % 2 else None, False)
    watts, temp, usable = slot_means(slots[slot_of(start)])
    assert (watts, temp, usable) == (1000, 20, True)
    add_sample(slots, start + 5, 10, 0, None, True)
    assert slot_means(slots[slot_of(start)])[2] is False  # curtailed
    add_sample(slots, start + SLOT, 10, 500, None, False)
    assert slot_means(slots[slot_of(start + SLOT)])[2] is False  # too short
