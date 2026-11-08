"""The generated dashboard: structure, placeholders and Jinja templates."""

from __future__ import annotations

from datetime import datetime
import json
import re
from typing import Any

import pytest

from custom_components.centro_control.panel import Light, PanelContext, build_panel

jinja2 = pytest.importorskip("jinja2")

IDS = {
    k: f"sensor.cc_{k}"
    for k in (
        "potencia_solar potencia_red potencia_importada potencia_exportada potencia_bateria potencia_consumo potencia_no_medida "
        "soc_bateria diferencia_soc energia_almacenada autonomia_bateria autosuficiencia_ahora uso_potencia_contratada precio_actual precio_excedentes "
        "periodo_tarifario energia_solar energia_importada energia_exportada energia_consumo energia_bateria_carga energia_bateria_descarga "
        "coste_energia compensacion_excedentes ahorro_solar factura_actual prevision_factura simulacion_factura autoconsumo autosuficiencia "
        "co2_evitado co2_emitido consumo_gas problemas luces_encendidas temperatura_interior humedad_interior historico"
    ).split()
}
IDS.update(
    {
        "periodo": "select.cc_periodo",
        "problema_critico": "binary_sensor.cc_problema_critico",
        "riego_activo": "binary_sensor.cc_riego_activo",
        "omitir_si_llueve": "switch.cc_omitir",
        "reconocer_problemas": "button.cc_reconocer",
        "apagar_luces": "button.cc_apagar",
        "regenerar_panel": "button.cc_regenerar",
        "parar_riego": "button.cc_parar",
        **{
            f"sim_{k}": f"number.cc_sim_{k}"
            for k in ("potencia_p1", "potencia_p2", "consumo", "precio", "paneles", "bateria", "excedentes")
        },
        "S1:energia_string": "sensor.s1_energia",
        "S2:energia_string": "sensor.s2_energia",
        "C1:energia_circuito": "sensor.c1_energia",
        "Z1:riego_restante": "sensor.z1_restante",
        "Z1:regar": "button.z1_regar",
        "Z1:minutos_riego": "number.z1_minutos",
    }
)


def context(**kw: Any) -> PanelContext:
    base = dict(
        title="Mi Casa",
        ids=IDS,
        settings={
            "red_potencia": "sensor.red",
            "precio_modo": "sensor",
            "precio_sensor": "sensor.precio",
            "solar_pico_wp": 6000,
            "inversor_temperatura": "sensor.inv_t",
            "lluvia_sensor": "binary_sensor.lluvia",
            "temperatura_exterior": "weather.casa",
        },
        strings=[
            {"id": "S1", "name": "Sur", "power": "sensor.pv1", "voltage": "sensor.pv1_v", "current": "sensor.pv1_a", "peak_wp": 3000},
            {"id": "S2", "name": "Oeste", "power": "sensor.pv2", "voltage": None, "current": None, "peak_wp": 3000},
        ],
        batteries=[
            {
                "id": "B1",
                "name": "Banco",
                "soc": "sensor.soc",
                "power": "sensor.bat",
                "voltage": "sensor.bat_v",
                "current": None,
                "temperatures": ["sensor.bat_t"],
                "cells": ["sensor.c1", "sensor.c2"],
                "cycles": "sensor.ciclos",
                "positive_charge": True,
            }
        ],
        circuits=[{"id": "C1", "name": "Cocina", "power": "sensor.cocina_w", "group": "Cuadro", "icon": "mdi:stove", "in_total": True}],
        zones=[{"id": "Z1", "name": "Césped", "valve": "switch.riego", "soil": "sensor.suelo"}],
        lights=[Light("light.salon", "Salón", False, True), Light("light.porche", "Porche", True, False)],
        climates=["climate.salon"],
        temperatures=["sensor.t_salon", "sensor.t_cocina"],
        humidities=["sensor.h_salon"],
        gas={
            "coste_hoy": "sensor.gas_coste_hoy",
            "caudal": "sensor.gas_caudal",
            "lectura": "sensor.gas_lectura",
            "factor_conversion": "number.gas_factor",
            "factura": "sensor.gas_factura",
        },
    )
    base.update(kw)
    return PanelContext(**base)


def _templates(node: Any, out: list[str]) -> list[str]:
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ("content", "primary", "secondary") and isinstance(value, str):
                out.append(value)
            else:
                _templates(value, out)
    elif isinstance(node, list):
        for item in node:
            _templates(item, out)
    return out


class FakeHA:
    """Just enough of Home Assistant's template environment to render."""

    def __init__(self) -> None:
        self.attrs: dict[str, dict[str, Any]] = {
            IDS["problemas"]: {
                "lista": [
                    {
                        "id": "a",
                        "nivel": "critico",
                        "area": "Batería",
                        "titulo": "Celdas",
                        "detalle": "Δ 120 mV",
                        "entidad": "sensor.c1",
                        "desde": "2026-11-06T10:00",
                        "reconocido": False,
                    },
                    {
                        "id": "b",
                        "nivel": "aviso",
                        "area": "Solar",
                        "titulo": "String",
                        "detalle": "−40 %",
                        "entidad": None,
                        "desde": "2026-11-06T11:00",
                        "reconocido": True,
                    },
                ],
                "criticos": 1,
                "avisos": 1,
                "info": 0,
            },
            IDS["potencia_consumo"]: {
                "circuitos": [{"nombre": "Cocina", "w": 800, "pct": 40, "periodo_kwh": 3.2, "icono": "mdi:stove", "padre": None}],
                "no_medido_w": 200,
            },
            IDS["potencia_solar"]: {
                "strings": [
                    {"nombre": "Sur", "w": 2000, "wp": 3000, "grupo": "A"},
                    {"nombre": "Oeste", "w": 900, "wp": 3000, "grupo": "A"},
                ],
                "rendimiento_pct": 48,
            },
            IDS["factura_actual"]: {
                "lineas": [{"concepto": "Energía", "calculo": "10 kWh × 0,15", "importe": 1.5}],
                "desde": "2026-11-01",
                "hasta": "2026-11-30",
                "dias": 6,
                "importada_kwh": 10,
                "base_imponible": 1.6,
                "iva_porcentaje": 21,
                "iva": 0.3,
                "total": 1.9,
                "compensacion_perdida": 0.4,
            },
            IDS["prevision_factura"]: {
                "proximas": [
                    {"mes": "2026-12", "fuente": "modelo", "consumo_kwh": 300, "importada_kwh": 200, "exportada_kwh": 50, "total": 60.1}
                ]
            },
            IDS["simulacion_factura"]: {
                "base": {"mes": "2026-12", "potencia": 10, "energia": 30, "compensacion": 2, "total": 50},
                "simulada": {"mes": "2026-12", "potencia": 8, "energia": 30, "compensacion": 2, "total": 47},
                "diferencia": -3,
                "diferencia_anual": -36,
            },
            IDS["co2_evitado"]: {
                b: {"evitado_kg": 1200.0, "red_kg": 3, "gas_kg": 2, "neto_kg": -4, "arboles": 2.1, "km_coche": 80}
                for b in ("hoy", "mes", "ano", "total")
            }
            | {"factor_red_kg_kwh": 0.102},
            IDS["luces_encendidas"]: {"encendidas": [{"nombre": "Salón"}], "total": 2, "interior": 1, "exterior": 0, "sin_conexion": 0},
            IDS["temperatura_interior"]: {"maxima": 23, "maxima_nombre": "Salón", "minima": 18, "minima_nombre": "Bodega"},
            IDS["consumo_gas"]: {"kwh": {"hoy": 5.0}, "mes": 12.0},
            "sensor.z1_restante": {"ultimo_riego": "2026-11-05T08:00", "ultimo_riego_minutos": 10},
        }

    def states(self, entity: str) -> str:
        return {"select.cc_periodo": "mes", "sensor.cc_potencia_red": "-350", "sensor.cc_autonomia_bateria": "unknown"}.get(entity, "12.5")

    def state_attr(self, entity: str, attr: str) -> Any:
        if attr in ("hoy", "ayer", "mes", "factura", "ano", "total") and entity not in (IDS["co2_evitado"],):
            return self.attrs.get(entity, {}).get(attr, 3.0)
        return self.attrs.get(entity, {}).get(attr, "Nombre" if attr == "friendly_name" else None)

    def env(self) -> Any:
        env = jinja2.Environment(extensions=["jinja2.ext.loopcontrols"])

        def _float(value: Any, default: Any = 0.0) -> Any:
            try:
                return float(value)
            except (TypeError, ValueError):
                return default

        def _int(value: Any, default: int = 0) -> int:
            try:
                return int(float(value))
            except (TypeError, ValueError):
                return default

        env.filters["float"] = _float
        env.filters["int"] = _int
        env.filters["states"] = self.states
        env.filters["timestamp_custom"] = lambda ts, fmt: datetime.fromtimestamp(ts).strftime(fmt) if ts else ""
        env.globals.update(
            states=self.states,
            state_attr=self.state_attr,
            now=lambda: datetime(2026, 11, 6, 12, 0),
            as_timestamp=lambda s: datetime.fromisoformat(s).timestamp() if s else None,
        )
        return env


def test_panel_structure():
    panel = build_panel(context())
    paths = [v["path"] for v in panel["views"]]
    assert paths == ["resumen", "red", "solar", "bateria", "consumos", "problemas", "coste", "co2", "gas", "luces", "clima", "riego"]
    text = json.dumps(panel, ensure_ascii=False)
    assert not re.search(r"@[a-zA-Z0-9_:]+", text.replace("@manu8613", "")), "placeholder left behind"
    assert "manu8613" in text  # credit
    for v in panel["views"]:
        assert v["type"] == "sections"
        for s in v["sections"]:
            assert s["cards"], v["path"]
            for card in s["cards"]:
                assert "type" in card


def test_templates_render():
    ha = FakeHA()
    env = ha.env()
    for template in _templates(build_panel(context()), []):
        rendered = env.from_string(template).render()
        assert "Undefined" not in rendered


def test_empty_installation():
    panel = build_panel(
        context(
            strings=[],
            batteries=[],
            circuits=[],
            zones=[],
            lights=[],
            climates=[],
            temperatures=[],
            humidities=[],
            gas={},
            settings={"red_potencia": "sensor.red"},
        )
    )
    assert len(panel["views"]) == 12
    env = FakeHA().env()
    for template in _templates(panel, []):
        env.from_string(template).render()


def test_yaml_dump_roundtrip():
    yaml = pytest.importorskip("yaml")
    panel = build_panel(context())
    assert yaml.safe_load(yaml.safe_dump(panel, allow_unicode=True)) == panel
