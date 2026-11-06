"""End-to-end tests in a real Home Assistant (pytest-homeassistant-custom-component)."""

from __future__ import annotations

from datetime import timedelta

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from homeassistant import config_entries  # noqa: E402
from homeassistant.config_entries import ConfigEntryState  # noqa: E402
from homeassistant.core import HomeAssistant  # noqa: E402
from homeassistant.data_entry_flow import FlowResultType  # noqa: E402
from homeassistant.helpers import entity_registry as er  # noqa: E402
from homeassistant.setup import async_setup_component  # noqa: E402
from homeassistant.util import dt as dt_util  # noqa: E402
from pytest_homeassistant_custom_component.common import (  # noqa: E402
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.centro_control.const import DOMAIN  # noqa: E402


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    return


@pytest.fixture(autouse=True)
async def madrid(hass):
    await hass.config.async_set_time_zone("Europe/Madrid")


@pytest.fixture
def expected_lingering_timers() -> bool:
    return True


OPTIONS = {
    "red_potencia": "sensor.red",
    "red_signo": "positivo_importa",
    "consumo_potencia": "sensor.casa",
    "crear_panel": False,
    "precio_modo": "unico",
    "precio_unico": 0.20,
    "excedentes_modo": "precio_fijo",
    "excedentes_precio": 0.05,
}

SUBENTRIES = [
    {
        "subentry_id": "S1",
        "subentry_type": "string",
        "title": "Sur",
        "unique_id": None,
        "data": {"nombre": "Sur", "potencia": "sensor.pv1", "pico_wp": 3000, "grupo": "A"},
    },
    {
        "subentry_id": "S2",
        "subentry_type": "string",
        "title": "Oeste",
        "unique_id": None,
        "data": {"nombre": "Oeste", "potencia": "sensor.pv2", "pico_wp": 3000, "grupo": "A"},
    },
    {
        "subentry_id": "B1",
        "subentry_type": "bateria",
        "title": "Banco",
        "unique_id": None,
        "data": {
            "nombre": "Banco",
            "soc": "sensor.soc",
            "potencia": "sensor.bat",
            "signo": "positivo_descarga",
            "capacidad_kwh": 10,
            "celdas": ["sensor.c1", "sensor.c2"],
        },
    },
    {
        "subentry_id": "C1",
        "subentry_type": "circuito",
        "title": "Cocina",
        "unique_id": None,
        "data": {"nombre": "Cocina", "potencia": "sensor.cocina", "grupo": "Cuadro", "suma_en_total": True},
    },
    {
        "subentry_id": "Z1",
        "subentry_type": "zona_riego",
        "title": "Césped",
        "unique_id": None,
        "data": {"nombre": "Césped", "valvula": "input_boolean.riego", "minutos": 5, "minutos_max": 30},
    },
]

STATES = {
    "sensor.red": ("500", {"unit_of_measurement": "W"}),
    "sensor.casa": ("2", {"unit_of_measurement": "kW"}),
    "sensor.pv1": ("1500", {"unit_of_measurement": "W"}),
    "sensor.pv2": ("700", {"unit_of_measurement": "W"}),
    "sensor.bat": ("-1000", {"unit_of_measurement": "W"}),
    "sensor.soc": ("60", {"unit_of_measurement": "%", "device_class": "battery"}),
    "sensor.c1": ("3.30", {}),
    "sensor.c2": ("3.42", {}),
    "sensor.cocina": ("300", {"unit_of_measurement": "W"}),
}


def set_states(hass: HomeAssistant, **changes: str) -> None:
    for entity, (value, attrs) in STATES.items():
        hass.states.async_set(entity, changes.get(entity, value), attrs)


def make_entry(**options) -> MockConfigEntry:
    return MockConfigEntry(domain=DOMAIN, title="Casa", data={}, options={**OPTIONS, **options}, subentries_data=SUBENTRIES)


async def setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    assert await async_setup_component(hass, "input_boolean", {"input_boolean": {"riego": None}})
    set_states(hass)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def eid(hass: HomeAssistant, entry: MockConfigEntry, key: str, platform: str = "sensor") -> str:
    entity_id = er.async_get(hass).async_get_entity_id(platform, DOMAIN, f"{entry.entry_id}_{key}")
    assert entity_id, key
    return entity_id


def value(hass, entry, key, platform="sensor"):
    return hass.states.get(eid(hass, entry, key, platform))


async def tick(hass: HomeAssistant, freezer, seconds: float = 10) -> None:
    freezer.tick(timedelta(seconds=seconds))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()


async def test_config_flow(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"nombre": "Mi casa", "red_potencia": "sensor.red", "red_signo": "positivo_importa", "crear_panel": False},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Mi casa"
    assert result["options"]["red_potencia"] == "sensor.red"
    assert "consumo_potencia" not in result["options"]


async def test_live_values(hass: HomeAssistant, freezer) -> None:
    freezer.move_to("2026-11-09 11:00:00+01:00")
    entry = make_entry()
    await setup(hass, entry)
    assert entry.state is ConfigEntryState.LOADED
    assert float(value(hass, entry, "potencia_solar").state) == 2200
    assert float(value(hass, entry, "potencia_red").state) == 500
    assert float(value(hass, entry, "potencia_consumo").state) == 2000
    assert float(value(hass, entry, "potencia_bateria").state) == -1000
    assert float(value(hass, entry, "soc_bateria").state) == 60
    assert float(value(hass, entry, "potencia_no_medida").state) == 1700
    assert value(hass, entry, "periodo_tarifario").state == "P1"
    strings = value(hass, entry, "potencia_solar").attributes["strings"]
    assert {s["nombre"] for s in strings} == {"Sur", "Oeste"}

    for _ in range(36):  # 6 minutes
        await tick(hass, freezer)
    imported = float(value(hass, entry, "energia_importada").state)
    assert imported == pytest.approx(0.5 * 0.1, rel=0.05)
    assert float(value(hass, entry, "coste_energia").state) == pytest.approx(imported * 0.20, abs=0.01)
    assert float(value(hass, entry, "energia_solar").state) == pytest.approx(2.2 * 0.1, rel=0.05)
    assert float(value(hass, entry, "co2_evitado").state) > 0
    assert value(hass, entry, "factura_actual").attributes["lineas"]


async def test_problems(hass: HomeAssistant, freezer) -> None:
    freezer.move_to("2026-11-09 12:00:00+01:00")
    hass.states.async_set("sun.sun", "above_horizon")
    entry = make_entry()
    await setup(hass, entry)
    # cells 120 mV apart: critical after 10 min
    for _ in range(25):
        await tick(hass, freezer, 30)
    problems = value(hass, entry, "problemas")
    ids = {p["id"] for p in problems.attributes["lista"]}
    assert "bat_delta_b1" in ids
    assert value(hass, entry, "problema_critico", "binary_sensor").state == "on"
    await hass.services.async_call("button", "press", {"entity_id": eid(hass, entry, "reconocer_problemas", "button")}, blocking=True)
    await hass.async_block_till_done()
    assert value(hass, entry, "problema_critico", "binary_sensor").state == "off"


async def test_irrigation(hass: HomeAssistant, freezer) -> None:
    freezer.move_to("2026-11-09 08:00:00+01:00")
    entry = make_entry()
    await setup(hass, entry)
    button = er.async_get(hass).async_get_entity_id("button", DOMAIN, f"{entry.entry_id}_Z1_regar")
    await hass.services.async_call("button", "press", {"entity_id": button}, blocking=True)
    await hass.async_block_till_done()
    assert hass.states.get("input_boolean.riego").state == "on"
    await tick(hass, freezer, 5 * 60 + 5)
    assert hass.states.get("input_boolean.riego").state == "off"
    remaining = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_Z1_riego_restante")
    assert hass.states.get(remaining).attributes["ultimo_riego_minutos"] == pytest.approx(5, abs=0.5)


async def test_options_menu_and_subentry(hass: HomeAssistant) -> None:
    entry = make_entry()
    await setup(hass, entry)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "tarifa"})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "precio_modo": "periodos",
            "precio_p1": 0.25,
            "precio_p2": 0.15,
            "precio_p3": 0.08,
            "precio_unico": 0.2,
            "excedentes_modo": "ninguna",
            "excedentes_precio": 0.0,
            "excedentes_tope": True,
            "potencia_precio_p1": 0.08,
            "potencia_precio_p2": 0.002,
            "impuesto_electrico": 5.11269632,
            "iva": 21,
            "alquiler_contador": 0.02663,
            "otros_fijos": 0.0,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options["precio_p1"] == 0.25
    assert entry.options["red_potencia"] == "sensor.red"  # other screens untouched

    result = await hass.config_entries.subentries.async_init((entry.entry_id, "circuito"), context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"nombre": "Lavadora", "potencia": "sensor.cocina", "grupo": "Aparatos", "suma_en_total": False}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert any(s.title == "Lavadora" for s in entry.subentries.values())


async def test_panel_builds_with_real_entities(hass: HomeAssistant) -> None:
    from custom_components.centro_control.dashboard import build_context
    from custom_components.centro_control.panel import build_panel

    hass.states.async_set("light.salon", "on", {"friendly_name": "Salón", "supported_color_modes": ["brightness"]})
    hass.states.async_set("sensor.t_salon", "21.5", {"device_class": "temperature", "unit_of_measurement": "°C"})
    entry = make_entry()
    await setup(hass, entry)
    ctx = build_context(hass, entry.runtime_data)
    assert ctx.ids["potencia_solar"].startswith("sensor.")
    assert "Z1:regar" in ctx.ids and ctx.ids["Z1:regar"].startswith("button.")
    assert ctx.lights[0].dimmable
    assert "sensor.t_salon" in ctx.temperatures
    panel = build_panel(ctx)
    assert len(panel["views"]) == 12

    import json

    from custom_components.centro_control.dashboard import panel_config

    config = panel_config(hass, entry.runtime_data)
    assert config["ids"]["potencia_solar"] == ctx.ids["potencia_solar"]
    assert config["author"] == "manu8613"
    json.dumps(config)  # must reach the browser as JSON


async def test_unload_and_persist(hass: HomeAssistant, freezer) -> None:
    freezer.move_to("2026-11-09 11:00:00+01:00")
    entry = make_entry()
    await setup(hass, entry)
    for _ in range(12):
        await tick(hass, freezer)
    before = float(value(hass, entry, "energia_importada").state)
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert float(value(hass, entry, "energia_importada").state) == pytest.approx(before, abs=0.002)
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_import_history_without_recorder(hass: HomeAssistant) -> None:
    entry = make_entry()
    await setup(hass, entry)
    await hass.services.async_call(DOMAIN, "importar_historico", {"dias": 30}, blocking=True)
    await hass.async_block_till_done()
    notes = hass.states.async_entity_ids("persistent_notification")
    assert isinstance(notes, list)


async def test_api_inventory_and_configuration(hass: HomeAssistant, hass_client) -> None:
    entry = make_entry()
    await setup(hass, entry)
    client = await hass_client()

    resp = await client.get("/api/centro_control/inventario")
    assert resp.status == 200
    inv = await resp.json()
    assert any(s["entity_id"] == "sensor.red" for s in inv["estados"])
    assert inv["centro_control"]["entradas"][0]["entry_id"] == entry.entry_id

    resp = await client.get("/api/centro_control/configuracion")
    config = await resp.json()
    item = config["entradas"][0]
    assert len(item["elementos"]) == 5
    item["opciones"]["precio_unico"] = 0.3
    item["elementos"].append(
        {
            "tipo": "circuito",
            "titulo": "Horno",
            "datos": {"nombre": "Horno", "potencia": "sensor.no_existe", "grupo": "Cuadro", "suma_en_total": False},
        }
    )

    resp = await client.post("/api/centro_control/configuracion", json={**config, "simular": True})
    body = await resp.json()
    assert body["simulado"] and "No existe sensor.no_existe" in body["avisos"]
    assert entry.options["precio_unico"] == 0.20  # nothing changed

    resp = await client.post("/api/centro_control/configuracion", json=config)
    body = await resp.json()
    assert body["ok"], body
    await hass.async_block_till_done()
    assert entry.options["precio_unico"] == 0.3
    assert len(entry.subentries) == 6
    assert entry.state is ConfigEntryState.LOADED
    assert body["copia"].endswith(".json")


async def test_api_requires_admin(hass: HomeAssistant, hass_client, hass_admin_user) -> None:
    entry = make_entry()
    await setup(hass, entry)
    hass_admin_user.groups = []
    client = await hass_client()
    resp = await client.get("/api/centro_control/inventario")
    assert resp.status == 403


async def test_api_status(hass: HomeAssistant, hass_client) -> None:
    entry = make_entry()
    await setup(hass, entry)
    client = await hass_client()
    resp = await client.get("/api/centro_control/estado")
    body = await resp.json()
    assert body["entidades"] > 30
    assert body["entradas"][0]["solar_w"] == 2200
