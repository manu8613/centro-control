"""Cloud cover / night grid charge advice with a real weather entity in Home Assistant."""

from __future__ import annotations

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from datetime import timedelta  # noqa: E402

from homeassistant.components.weather import Forecast, WeatherEntity, WeatherEntityFeature  # noqa: E402
from homeassistant.const import UnitOfTemperature  # noqa: E402
from homeassistant.setup import async_setup_component  # noqa: E402
from homeassistant.util import dt as dt_util  # noqa: E402
from pytest_homeassistant_custom_component.common import MockPlatform, mock_platform  # noqa: E402

from .test_init import (  # noqa: E402,F401
    auto_enable_custom_integrations,
    expected_lingering_timers,
    madrid,
    make_entry,
    setup,
    tick,
    value,
)


class FakeWeather(WeatherEntity):
    _attr_name = "Forecast Casa"
    _attr_native_temperature = 12.0
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_condition = "partlycloudy"
    _attr_supported_features = WeatherEntityFeature.FORECAST_DAILY

    async def async_forecast_daily(self):
        base = dt_util.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return [
            Forecast(datetime=(base + timedelta(days=i)).isoformat(), native_temperature=14.0, condition="cloudy", cloud_coverage=20 + 10 * i)
            for i in range(6)
        ]


class HourlyOnlyWeather(FakeWeather):
    """Like some integrations: no daily forecast, only hourly."""

    _attr_supported_features = WeatherEntityFeature.FORECAST_HOURLY

    async def async_forecast_hourly(self):
        base = dt_util.now().replace(minute=0, second=0, microsecond=0)
        return [Forecast(datetime=(base + timedelta(hours=i)).isoformat(), native_temperature=10.0, condition="cloudy", cloud_coverage=50) for i in range(72)]


class NoForecastWeather(WeatherEntity):
    _attr_name = "Forecast Casa"
    _attr_native_temperature = 12.0
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_condition = "rainy"


async def add_weather(hass, cls=FakeWeather) -> str:
    async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
        async_add_entities([cls()])

    mock_platform(hass, "test.weather", MockPlatform(async_setup_platform=async_setup_platform))
    assert await async_setup_component(hass, "weather", {"weather": {"platform": "test"}})
    await hass.async_block_till_done()
    return "weather.forecast_casa"


async def test_weather_forecast_reaches_the_sensor(hass, freezer) -> None:
    wid = await add_weather(hass)
    entry = make_entry(meteo_entidad=wid, solar_potencia="sensor.pv1")
    await setup(hass, entry)
    for _ in range(3):
        await tick(hass, freezer, 10)
    state = value(hass, entry, "recomendacion_carga_red")
    assert state.attributes.get("dias"), state.attributes


async def test_hourly_only_weather_still_gives_cloud_cover(hass, freezer) -> None:
    wid = await add_weather(hass, HourlyOnlyWeather)
    entry = make_entry(meteo_entidad=wid)
    await setup(hass, entry)
    for _ in range(3):
        await tick(hass, freezer, 10)
    attrs = value(hass, entry, "recomendacion_carga_red").attributes
    assert attrs["dias"] and attrs["dias"][0]["nubes_pct"] == 50, attrs
    assert attrs["meteo"]["tipo"] == "hourly"


async def test_weather_without_forecast_uses_current_state_and_explains(hass, freezer) -> None:
    wid = await add_weather(hass, NoForecastWeather)
    entry = make_entry(meteo_entidad=wid)
    await setup(hass, entry)
    for _ in range(3):
        await tick(hass, freezer, 10)
    attrs = value(hass, entry, "recomendacion_carga_red").attributes
    assert [d["nubes_pct"] for d in attrs["dias"]] == [95]  # "rainy" today from the entity's state
    assert "daily" in attrs["meteo"]["error"], attrs["meteo"]


async def test_missing_weather_entity_is_explained(hass, freezer) -> None:
    entry = make_entry(meteo_entidad="weather.no_existe")
    await setup(hass, entry)
    for _ in range(3):
        await tick(hass, freezer, 10)
    attrs = value(hass, entry, "recomendacion_carga_red").attributes
    assert attrs["dias"] == [] and "no existe" in attrs["meteo"]["error"], attrs
