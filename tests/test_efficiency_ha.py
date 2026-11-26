"""Real efficiency of the PV strings inside Home Assistant (sensor and Open-Meteo)."""

from __future__ import annotations

from datetime import timedelta

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.centro_control.const import DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


STRING = {"nombre": "Tejado", "potencia": "sensor.pv1", "pico_wp": 5355, "grupo": "A", "coef_temp_pmax": -0.26, "noct": 47.6, "eficiencia_modulo": 23.0}


def _entry(string: dict) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="Casa",
        data={},
        options={"red_potencia": "sensor.red", "red_signo": "positivo_importa", "crear_panel": False, "temperatura_exterior": "sensor.exterior"},
        subentries_data=[{"subentry_id": "S1", "subentry_type": "string", "title": "Tejado", "unique_id": None, "data": string}],
    )


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    hass.states.async_set("sensor.red", "0", {"unit_of_measurement": "W"})
    hass.states.async_set("sensor.pv1", "3900", {"unit_of_measurement": "W"})
    hass.states.async_set("sensor.exterior", "10", {"unit_of_measurement": "°C"})
    hass.states.async_set("sensor.irr", "800", {"unit_of_measurement": "W/m²"})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def _sensor(hass, entry, unique):
    entity_id = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_{unique}")
    assert entity_id, unique
    return hass.states.get(entity_id)


async def test_efficiency_with_irradiance_sensor(hass: HomeAssistant, freezer) -> None:
    freezer.move_to("2026-06-10 12:00:00+02:00")
    entry = _entry({**STRING, "irradiancia": "sensor.irr"})
    await _setup(hass, entry)
    string = _sensor(hass, entry, "S1_rendimiento_string")
    expected = 5355 * 0.8 * (1 - 0.0026 * 12.6)
    assert float(string.state) == pytest.approx(100 * 3900 / expected, abs=0.1)
    assert string.attributes["fuente"] == "sensor"
    assert string.attributes["t_celda"] == pytest.approx(37.6)
    assert float(_sensor(hass, entry, "rendimiento_solar").state) == pytest.approx(float(string.state), abs=0.2)
    for _ in range(36):  # 6 minutes
        freezer.tick(timedelta(seconds=10))
        async_fire_time_changed(hass, dt_util.utcnow())
        await hass.async_block_till_done()
    assert float(_sensor(hass, entry, "rendimiento_solar_hoy").state) == pytest.approx(float(string.state), abs=1)
    assert _sensor(hass, entry, "S1_rendimiento_string").attributes["rendimiento_mes_pct"] is not None


async def test_efficiency_with_open_meteo(hass: HomeAssistant, freezer, aioclient_mock) -> None:
    freezer.move_to("2026-06-10 12:00:00+02:00")
    now = dt_util.utcnow().timestamp()
    aioclient_mock.get(
        "https://api.open-meteo.com/v1/forecast",
        json={"minutely_15": {"time": [now - 900, now + 900], "global_tilted_irradiance_instant": [800, 800], "temperature_2m": [30, 30]}},
    )
    entry = _entry({**STRING, "inclinacion": 30, "orientacion": 180})
    await _setup(hass, entry)
    freezer.tick(timedelta(seconds=10))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    string = _sensor(hass, entry, "S1_rendimiento_string")
    assert string.attributes["fuente"] == "open-meteo"
    assert string.attributes["irradiancia_wm2"] == 800
    assert string.attributes["t_ambiente"] == 10  # the configured outdoor sensor wins over the model
    assert float(string.state) > 90
    assert aioclient_mock.mock_calls[0][1].query["azimuth"] == "0"


async def test_string_without_mounting_has_no_efficiency(hass: HomeAssistant) -> None:
    entry = _entry(STRING)
    await _setup(hass, entry)
    string = _sensor(hass, entry, "S1_rendimiento_string")
    assert string.state == "unknown"
    assert "inclinación" in string.attributes["estado"]


async def test_efficiency_measured_with_siar(hass: HomeAssistant, freezer, aioclient_mock) -> None:
    from custom_components.centro_control.dashboard import panel_config
    from custom_components.centro_control.siar import SIAR_URL

    from .test_siar import clear_rows

    hass.config.latitude, hass.config.longitude = 42.0, -4.5
    await hass.config.async_set_time_zone("Europe/Madrid")
    freezer.move_to("2026-06-10 11:00:00+02:00")
    now = dt_util.utcnow().timestamp()
    aioclient_mock.get("https://api.open-meteo.com/v1/forecast", json={"minutely_15": {"time": [now - 900, now + 9000], "global_tilted_irradiance_instant": [800, 800], "temperature_2m": [20, 20]}})
    aioclient_mock.get(f"{SIAR_URL}/Autenticacion/cifrarCadena", text='"cifrado"')
    aioclient_mock.get(f"{SIAR_URL}/Autenticacion/obtenerToken", json="token-de-prueba")
    aioclient_mock.get(f"{SIAR_URL}/Datos/Horarios/ESTACION", json={"Datos": clear_rows(dt_util.now().date(), 0)})
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Casa",
        data={},
        options={**_entry(STRING).options, "siar_estacion": "xx01", "siar_usuario": "12345678Z", "siar_clave": "secreta"},
        subentries_data=[{"subentry_id": "S1", "subentry_type": "string", "title": "Tejado", "unique_id": None, "data": {**STRING, "inclinacion": 30, "orientacion": 180}}],
    )
    await _setup(hass, entry)
    for _ in range(6 * 75):  # 75 minutes of 10 s ticks
        freezer.tick(timedelta(seconds=10))
        async_fire_time_changed(hass, dt_util.utcnow())
        await hass.async_block_till_done()
    # the station gave data, the clock is UTC and the half hours with power are compared
    data_call = next(c for c in aioclient_mock.mock_calls if "Datos" in str(c[1]))
    assert data_call[1].query["Id"] == "XX01" and data_call[1].query["token"] == "token-de-prueba"
    siar = _sensor(hass, entry, "rendimiento_solar_siar")
    assert siar.attributes["estacion"] == "XX01"
    assert siar.attributes["hora_estacion"] == "UTC"
    assert not siar.attributes["error"]
    hoy = siar.attributes["siar_hoy_pct"]
    assert hoy is not None and 50 < hoy < 120
    string = _sensor(hass, entry, "S1_rendimiento_string")
    assert string.attributes["siar_tramo_pct"] is not None
    # the credentials never reach the panel
    config = panel_config(hass, entry.runtime_data)
    assert "siar_clave" not in config["settings"] and "siar_usuario" not in config["settings"]
    assert "secreta" not in str(config)


def test_exports_hide_the_siar_password():
    from custom_components.centro_control.api import _entry_dict, _keep_secrets

    entry = MockConfigEntry(domain=DOMAIN, title="Casa", data={}, options={"siar_estacion": "XX01", "siar_usuario": "12345678Z", "siar_clave": "secreta"})
    exported = _entry_dict(entry)["opciones"]
    assert exported["siar_clave"] == "**********" and exported["siar_usuario"] == "**********"
    assert exported["siar_estacion"] == "XX01"
    assert _keep_secrets(dict(exported), entry.options)["siar_clave"] == "secreta"
    assert "siar_clave" not in _keep_secrets(dict(exported), {})
