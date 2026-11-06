"""Problem detection."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from custom_components.centro_control.model import Model
from custom_components.centro_control.problems import Debouncer, Live, evaluate

NOW = datetime(2026, 11, 6, 12, 0)


@dataclass
class St:
    entity_id: str
    state: str
    attributes: dict[str, Any] = field(default_factory=dict)
    last_changed: datetime = NOW


def make(states: dict[str, Any], attrs: dict[str, dict] | None = None):
    attrs = attrs or {}
    table = {k: St(k, str(v), attrs.get(k, {})) for k, v in states.items()}
    return table.get, list(table.values())


def model(**options) -> Model:
    subs = [
        ("s1", "string", {"nombre": "String 1", "potencia": "sensor.pv1", "pico_wp": 2000, "grupo": "Sur"}),
        ("s2", "string", {"nombre": "String 2", "potencia": "sensor.pv2", "pico_wp": 2000, "grupo": "Sur"}),
        (
            "b1",
            "bateria",
            {
                "nombre": "Batería 1",
                "soc": "sensor.soc",
                "potencia": "sensor.bat_w",
                "capacidad_kwh": 16,
                "celdas": ["sensor.c1", "sensor.c2", "sensor.c3"],
                "alarmas": "sensor.bms_alarm",
            },
        ),
        ("c1", "circuito", {"nombre": "Cocina", "potencia": "sensor.cocina"}),
    ]
    base = {"red_potencia": "sensor.grid", "revisar_baterias": True}
    return Model.build({}, {**base, **options}, subs)


def ids(problems):
    return {p.id for p in problems}


def test_string_underperforming_and_dead():
    m = model()
    get, states = make({"sensor.pv1": 1500, "sensor.pv2": 700, "sensor.grid": 0, "sensor.soc": 50, "sensor.bat_w": 0, "sensor.cocina": 100})
    found = evaluate(m, get, states, Live(pv_w=2200, is_day=True), NOW)
    assert "string_bajo_s2" in ids(found)
    get, states = make({"sensor.pv1": 1500, "sensor.pv2": 0, "sensor.grid": 0, "sensor.soc": 50, "sensor.bat_w": 0, "sensor.cocina": 100})
    found = evaluate(m, get, states, Live(pv_w=1500, is_day=True), NOW)
    assert "string_cero_s2" in ids(found)
    assert next(p for p in found if p.id == "string_cero_s2").level == "critico"
    # at night nothing is said
    assert not {i for i in ids(evaluate(m, get, states, Live(is_day=False), NOW)) if i.startswith("string")}


def test_cells_and_bms_alarm():
    m = model()
    get, states = make(
        {
            "sensor.c1": 3.30,
            "sensor.c2": 3.41,
            "sensor.c3": 3.31,
            "sensor.bms_alarm": "Cell overvoltage",
            "sensor.soc": 80,
            "sensor.bat_w": 0,
            "sensor.pv1": 0,
            "sensor.pv2": 0,
            "sensor.grid": 0,
            "sensor.cocina": 0,
        }
    )
    found = {p.id: p for p in evaluate(m, get, states, Live(), NOW)}
    assert found["bat_delta_b1"].level == "critico"
    assert "celda 2 la más alta" in found["bat_delta_b1"].detail
    assert found["bat_alarma_b1"].level == "critico"


def test_unavailable_and_device_batteries():
    m = model()
    get, states = make(
        {"sensor.grid": "unavailable", "sensor.puerta_battery": 4, "sensor.soc": 9},
        {"sensor.puerta_battery": {"device_class": "battery", "friendly_name": "Puerta"}, "sensor.soc": {"device_class": "battery"}},
    )
    found = {p.id: p for p in evaluate(m, get, states, Live(), NOW)}
    assert "nodisp_sensor.grid" in found
    assert found["pila_sensor.puerta_battery"].level == "critico"
    assert "pila_sensor.soc" not in found  # the house battery is not a device battery
    assert "bat_soc_b1" in found


def test_grid_import_with_full_battery():
    m = model()
    get, states = make({"sensor.grid": 800, "sensor.soc": 90, "sensor.bat_w": 0, "sensor.pv1": 0, "sensor.pv2": 0, "sensor.cocina": 0})
    found = ids(evaluate(m, get, states, Live(grid_w=800, soc=90, battery_w=0), NOW))
    assert "red_con_bateria" in found


def test_circuits_vs_total():
    m = model()
    get, states = make({})
    found = ids(evaluate(m, get, states, Live(load_w=1000, circuits_w=1600), NOW))
    assert "consumo_suma" in found
    found = ids(evaluate(m, get, states, Live(load_w=3000, circuits_w=500), NOW))
    assert "consumo_no_medido" in found


def test_debouncer():
    m = model()
    get, states = make({"sensor.grid": "unavailable"})
    problems = [p for p in evaluate(m, get, states, Live(), NOW) if p.id == "nodisp_sensor.grid"]
    d = Debouncer()
    assert d.update(problems, NOW) == []
    assert d.update(problems, NOW + timedelta(minutes=11))[0][1] == NOW
    assert d.update([], NOW + timedelta(minutes=12)) == []
    assert d.first_seen == {}
