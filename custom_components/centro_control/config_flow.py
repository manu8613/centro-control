"""Configuration screens for Centro de Control.

* First screen: name, grid meter and the panel.
* "Configurar": a menu with one screen per area (red, solar, tarifa...).
* Strings, batteries, circuits and irrigation zones are *subentries*: each one
  is added, edited or deleted on its own from the integration page.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    OptionsFlow,
    SubentryFlowResult,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    IconSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .compat import vol
from .const import (
    BAT_POSITIVE_CHARGE,
    BAT_POSITIVE_DISCHARGE,
    CONF_ALARMS,
    CONF_BATTERY_SIGN,
    CONF_BATTERY_TEMP_MAX,
    CONF_BILLING_DAY,
    CONF_CAPACITY,
    CONF_CELL_DELTA_CRIT,
    CONF_CELL_DELTA_WARN,
    CONF_CELL_DIFF,
    CONF_CELL_HIGH,
    CONF_CELL_LOW,
    CONF_CELL_MAX,
    CONF_CELL_MIN,
    CONF_CELLS,
    CONF_CHECK_DEVICE_BATTERIES,
    CONF_CHECK_GRID_WITH_BATTERY,
    CONF_CHECK_SAFETY,
    CONF_CLIMATES,
    CONF_CO2_CAR,
    CONF_CO2_FACTOR,
    CONF_CO2_GAS,
    CONF_CO2_SENSOR,
    CONF_CO2_TREE,
    CONF_CONTRACTED_P1,
    CONF_CONTRACTED_P2,
    CONF_CREATE_DASHBOARD,
    CONF_CURRENT,
    CONF_CYCLES,
    CONF_LINK,
    CONF_BANK,
    CONF_DEVICE_BATTERY_MIN,
    CONF_ELECTRICITY_TAX,
    CONF_ENERGY,
    CONF_EXPORT_CAP,
    CONF_EXPORT_MODE,
    CONF_EXPORT_PRICE,
    CONF_EXPORT_SENSOR,
    CONF_GAS_AUTO,
    CONF_GAS_BILL,
    CONF_GAS_COST_MONTH,
    CONF_GAS_COST_TODAY,
    CONF_GAS_FACTOR,
    CONF_GAS_FLOW,
    CONF_GAS_FLOW_HOURS,
    CONF_GAS_METER,
    CONF_GRID_EXPORT_ENERGY,
    CONF_GRID_FREQUENCY,
    CONF_GRID_IMPORT_ENERGY,
    CONF_GRID_POWER,
    CONF_GRID_SIGN,
    CONF_GRID_VOLTAGE,
    CONF_GROUP,
    CONF_HUMIDITIES,
    CONF_HUMIDITY_MAX,
    CONF_ICON,
    CONF_IN_TOTAL,
    CONF_INV_ALARM,
    CONF_INV_FAULT,
    CONF_INV_STATUS,
    CONF_INV_TEMP,
    CONF_INV_TEMP2,
    CONF_DAY_SHARE,
    CONF_DEYE_GRID_CHARGE,
    CONF_DEYE_GRID_CURRENT,
    CONF_DEYE_P1_CHARGE,
    CONF_DEYE_P1_POWER,
    CONF_DEYE_P1_SOC,
    CONF_DEYE_P1_TIME,
    CONF_DEYE_P2_CHARGE,
    CONF_DEYE_P2_POWER,
    CONF_DEYE_P2_SOC,
    CONF_DEYE_P2_TIME,
    CONF_DEYE_TOU,
    CONF_WEATHER,
    CONF_INV_TEMP_CRIT,
    CONF_INV_TEMP_WARN,
    CONF_LIGHTS,
    CONF_LIGHTS_EXCLUDE,
    CONF_LOAD_ENERGY,
    CONF_LOAD_POWER,
    CONF_MAX_MINUTES,
    CONF_METER_RENTAL,
    CONF_MINUTES,
    CONF_NAME,
    CONF_NOTIFY_LEVEL,
    CONF_NOTIFY_SERVICE,
    CONF_OTHER_FIXED,
    CONF_OUTDOOR_PATTERN,
    CONF_OUTDOOR_TEMP,
    CONF_PARENT,
    CONF_PEAK,
    CONF_POWER,
    CONF_POWER_PRICE_P1,
    CONF_POWER_PRICE_P2,
    CONF_PRICE_FLAT,
    CONF_PRICE_MODE,
    CONF_PRICE_P1,
    CONF_PRICE_P2,
    CONF_PRICE_P3,
    CONF_PRICE_SENSOR,
    CONF_PV_ENERGY,
    CONF_PV_FORECAST,
    CONF_PV_FORECAST_TOMORROW,
    CONF_PV_PEAK,
    CONF_PV_POWER,
    CONF_RAIN_SENSOR,
    CONF_SOC,
    CONF_SOC_DIFF_CRIT,
    CONF_SOC_DIFF_WARN,
    CONF_SOC_MIN,
    CONF_SOIL,
    CONF_SOIL_MIN,
    CONF_STRING_TOLERANCE,
    CONF_TEMP_EXCLUDE_PATTERN,
    CONF_TEMP_MAX,
    CONF_TEMP_MIN,
    CONF_TEMPERATURE,
    CONF_TEMPERATURES,
    CONF_UNMEASURED_MAX,
    CONF_VALVE,
    CONF_VAT,
    CONF_VOLTAGE,
    CONF_VOLTAGE_MAX,
    CONF_VOLTAGE_MIN,
    DEFAULT_TITLE,
    DEFAULTS,
    DOMAIN,
    EXPORT_FIXED,
    EXPORT_NONE,
    EXPORT_SENSOR,
    GRID_POSITIVE_EXPORT,
    GRID_POSITIVE_IMPORT,
    LEVELS,
    PRICE_FLAT,
    PRICE_PERIODS,
    PRICE_SENSOR,
    SUB_BATTERY,
    SUB_CIRCUIT,
    SUB_STRING,
    SUB_ZONE,
)

# ---------------------------------------------------------------------- selectors


def _entity(domains: str | list[str] = "sensor", multiple: bool = False, device_class: str | None = None) -> EntitySelector:
    config = EntitySelectorConfig(domain=domains, multiple=multiple)
    if device_class:
        config["device_class"] = device_class
    return EntitySelector(config)


def _number(minimum: float, maximum: float, step: float | str = "any", unit: str | None = None, slider: bool = False) -> NumberSelector:
    config = NumberSelectorConfig(min=minimum, max=maximum, step=step, mode=NumberSelectorMode.SLIDER if slider else NumberSelectorMode.BOX)
    if unit:
        config["unit_of_measurement"] = unit
    return NumberSelector(config)


def _select(options: list[str] | tuple[str, ...], key: str) -> SelectSelector:
    return SelectSelector(SelectSelectorConfig(options=list(options), translation_key=key, mode=SelectSelectorMode.DROPDOWN))


SENSOR = _entity("sensor")
POWER = _entity("sensor")
ENERGY = _entity("sensor")
ANY_STATUS = _entity(["sensor", "binary_sensor"])
SWITCH = _entity(["switch", "input_boolean"])
NUMBER = _entity(["number", "input_number"])
TIME = _entity(["time", "input_datetime", "text"])
CHARGE_MODE = _entity(["select", "switch", "input_boolean", "input_select"])

# Each options screen: key -> (selector, required)
Fields = dict[str, tuple[Any, bool]]

SECTIONS: dict[str, Fields] = {
    "general": {
        CONF_CREATE_DASHBOARD: (BooleanSelector(), True),
        CONF_BILLING_DAY: (_number(1, 28, 1, "día"), True),
        CONF_NOTIFY_SERVICE: (TextSelector(), False),
        CONF_NOTIFY_LEVEL: (_select(LEVELS, CONF_NOTIFY_LEVEL), True),
    },
    "red": {
        CONF_GRID_POWER: (POWER, True),
        CONF_GRID_SIGN: (_select([GRID_POSITIVE_IMPORT, GRID_POSITIVE_EXPORT], CONF_GRID_SIGN), True),
        CONF_GRID_IMPORT_ENERGY: (ENERGY, False),
        CONF_GRID_EXPORT_ENERGY: (ENERGY, False),
        CONF_GRID_VOLTAGE: (SENSOR, False),
        CONF_GRID_FREQUENCY: (SENSOR, False),
        CONF_CONTRACTED_P1: (_number(0, 15, 0.01, "kW"), True),
        CONF_CONTRACTED_P2: (_number(0, 15, 0.01, "kW"), True),
    },
    "consumo": {
        CONF_LOAD_POWER: (POWER, False),
        CONF_LOAD_ENERGY: (ENERGY, False),
    },
    "solar": {
        CONF_PV_POWER: (POWER, False),
        CONF_PV_ENERGY: (ENERGY, False),
        CONF_PV_FORECAST: (SENSOR, False),
        CONF_PV_PEAK: (_number(0, 100000, 1, "Wp"), True),
        CONF_INV_TEMP: (SENSOR, False),
        CONF_INV_TEMP2: (SENSOR, False),
        CONF_INV_STATUS: (ANY_STATUS, False),
        CONF_INV_FAULT: (ANY_STATUS, False),
        CONF_INV_ALARM: (ANY_STATUS, False),
        CONF_PV_FORECAST_TOMORROW: (SENSOR, False),
        CONF_WEATHER: (_entity("weather"), False),
        CONF_DAY_SHARE: (_number(30, 100, 1, "%"), True),
    },
    "deye": {
        CONF_DEYE_GRID_CHARGE: (SWITCH, False),
        CONF_DEYE_GRID_CURRENT: (NUMBER, False),
        CONF_DEYE_TOU: (SWITCH, False),
        CONF_DEYE_P1_TIME: (TIME, False),
        CONF_DEYE_P1_POWER: (NUMBER, False),
        CONF_DEYE_P1_SOC: (NUMBER, False),
        CONF_DEYE_P1_CHARGE: (CHARGE_MODE, False),
        CONF_DEYE_P2_TIME: (TIME, False),
        CONF_DEYE_P2_POWER: (NUMBER, False),
        CONF_DEYE_P2_SOC: (NUMBER, False),
        CONF_DEYE_P2_CHARGE: (CHARGE_MODE, False),
    },
    "tarifa": {
        CONF_PRICE_MODE: (_select([PRICE_PERIODS, PRICE_SENSOR, PRICE_FLAT], CONF_PRICE_MODE), True),
        CONF_PRICE_SENSOR: (SENSOR, False),
        CONF_PRICE_P1: (_number(0, 2, "any", "€/kWh"), True),
        CONF_PRICE_P2: (_number(0, 2, "any", "€/kWh"), True),
        CONF_PRICE_P3: (_number(0, 2, "any", "€/kWh"), True),
        CONF_PRICE_FLAT: (_number(0, 2, "any", "€/kWh"), True),
        CONF_EXPORT_MODE: (_select([EXPORT_FIXED, EXPORT_SENSOR, EXPORT_NONE], CONF_EXPORT_MODE), True),
        CONF_EXPORT_PRICE: (_number(0, 2, "any", "€/kWh"), True),
        CONF_EXPORT_SENSOR: (SENSOR, False),
        CONF_EXPORT_CAP: (BooleanSelector(), True),
        CONF_POWER_PRICE_P1: (_number(0, 1, "any", "€/kW·día"), True),
        CONF_POWER_PRICE_P2: (_number(0, 1, "any", "€/kW·día"), True),
        CONF_ELECTRICITY_TAX: (_number(0, 30, "any", "%"), True),
        CONF_VAT: (_number(0, 30, "any", "%"), True),
        CONF_METER_RENTAL: (_number(0, 2, "any", "€/día"), True),
        CONF_OTHER_FIXED: (_number(0, 5, "any", "€/día"), True),
    },
    "gas": {
        CONF_GAS_AUTO: (BooleanSelector(), True),
        CONF_GAS_METER: (SENSOR, False),
        CONF_GAS_FACTOR: (_number(5, 15, "any", "kWh/m³"), True),
        CONF_GAS_COST_TODAY: (SENSOR, False),
        CONF_GAS_COST_MONTH: (SENSOR, False),
        CONF_GAS_BILL: (SENSOR, False),
        CONF_GAS_FLOW: (SENSOR, False),
    },
    "luces": {
        CONF_LIGHTS: (_entity("light", multiple=True), False),
        CONF_LIGHTS_EXCLUDE: (_entity("light", multiple=True), False),
        CONF_OUTDOOR_PATTERN: (TextSelector(), False),
    },
    "clima": {
        CONF_CLIMATES: (_entity("climate", multiple=True), False),
        CONF_TEMPERATURES: (_entity("sensor", multiple=True, device_class="temperature"), False),
        CONF_HUMIDITIES: (_entity("sensor", multiple=True, device_class="humidity"), False),
        CONF_OUTDOOR_TEMP: (_entity(["sensor", "weather"]), False),
        CONF_TEMP_EXCLUDE_PATTERN: (TextSelector(), False),
        CONF_TEMP_MAX: (_number(15, 50, 0.5, "°C"), True),
        CONF_TEMP_MIN: (_number(-10, 25, 0.5, "°C"), True),
        CONF_HUMIDITY_MAX: (_number(40, 100, 1, "%"), True),
    },
    "riego": {
        CONF_RAIN_SENSOR: (_entity(["binary_sensor", "sensor", "weather"]), False),
        CONF_SOIL_MIN: (_number(0, 100, 1, "%"), True),
    },
    "co2": {
        CONF_CO2_FACTOR: (_number(0, 2, "any", "kg/kWh"), True),
        CONF_CO2_SENSOR: (SENSOR, False),
        CONF_CO2_GAS: (_number(0, 1, "any", "kg/kWh"), True),
        CONF_CO2_TREE: (_number(1, 100, "any", "kg/año"), True),
        CONF_CO2_CAR: (_number(0.01, 1, "any", "kg/km"), True),
    },
    "problemas": {
        CONF_STRING_TOLERANCE: (_number(5, 90, 1, "%"), True),
        CONF_CELL_DELTA_WARN: (_number(0.005, 0.5, "any", "V"), True),
        CONF_CELL_DELTA_CRIT: (_number(0.01, 1, "any", "V"), True),
        CONF_CELL_MIN: (_number(1, 4, "any", "V"), True),
        CONF_CELL_MAX: (_number(2, 5, "any", "V"), True),
        CONF_BATTERY_TEMP_MAX: (_number(20, 80, 1, "°C"), True),
        CONF_SOC_MIN: (_number(0, 100, 1, "%"), True),
        CONF_SOC_DIFF_WARN: (_number(1, 100, 0.5, "%"), True),
        CONF_SOC_DIFF_CRIT: (_number(1, 100, 0.5, "%"), True),
        CONF_INV_TEMP_WARN: (_number(20, 120, 1, "°C"), True),
        CONF_INV_TEMP_CRIT: (_number(20, 120, 1, "°C"), True),
        CONF_VOLTAGE_MIN: (_number(100, 260, 1, "V"), True),
        CONF_VOLTAGE_MAX: (_number(200, 270, 1, "V"), True),
        CONF_UNMEASURED_MAX: (_number(0, 20000, 10, "W"), True),
        CONF_CHECK_GRID_WITH_BATTERY: (BooleanSelector(), True),
        CONF_CHECK_DEVICE_BATTERIES: (BooleanSelector(), True),
        CONF_DEVICE_BATTERY_MIN: (_number(1, 50, 1, "%"), True),
        CONF_CHECK_SAFETY: (BooleanSelector(), True),
        CONF_GAS_FLOW_HOURS: (_number(1, 48, 0.5, "h"), True),
    },
}


def _schema(fields: Fields, values: dict[str, Any]) -> vol.Schema:
    return vol.Schema(_schema_dict(fields, values))


def _schema_dict(fields: Fields, values: dict[str, Any]) -> dict[Any, Any]:
    schema: dict[Any, Any] = {}
    for key, (selector, required) in fields.items():
        current = values.get(key, DEFAULTS.get(key))
        if required:
            marker = vol.Required(key) if current is None else vol.Required(key, default=current)
            schema[marker] = selector
        else:
            schema[vol.Optional(key, description={"suggested_value": current})] = selector
    return schema


def _merge(fields: Fields, old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Apply one screen; optional fields left empty are removed."""
    out = dict(old)
    for key in fields:
        if key in new and new[key] not in (None, "", []):
            out[key] = new[key]
        else:
            out.pop(key, None)
    return out


# ---------------------------------------------------------------------- main flow


class CentroConfigFlow(ConfigFlow, domain=DOMAIN):
    """Create a Centro de Control."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        fields: Fields = {
            CONF_GRID_POWER: (POWER, True),
            CONF_GRID_SIGN: SECTIONS["red"][CONF_GRID_SIGN],
            CONF_LOAD_POWER: (POWER, False),
            CONF_PV_POWER: (POWER, False),
            CONF_CREATE_DASHBOARD: (BooleanSelector(), True),
        }
        if user_input is not None:
            title = str(user_input.pop(CONF_NAME, DEFAULT_TITLE)).strip() or DEFAULT_TITLE
            return self.async_create_entry(title=title, data={}, options=_merge(fields, {}, user_input))
        schema = vol.Schema({vol.Required(CONF_NAME, default=DEFAULT_TITLE): TextSelector(), **_schema_dict(fields, {})})
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> CentroOptionsFlow:
        return CentroOptionsFlow()

    @classmethod
    @callback
    def async_get_supported_subentry_types(cls, config_entry: ConfigEntry) -> dict[str, type[ConfigSubentryFlow]]:
        return {
            SUB_STRING: StringFlow,
            SUB_BATTERY: BatteryFlow,
            SUB_CIRCUIT: CircuitFlow,
            SUB_ZONE: ZoneFlow,
        }


class CentroOptionsFlow(OptionsFlow):
    """Menu with one screen per area."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_show_menu(step_id="init", menu_options=list(SECTIONS))

    async def _section(self, name: str, user_input: dict[str, Any] | None) -> ConfigFlowResult:
        fields = SECTIONS[name]
        values = {**self.config_entry.data, **self.config_entry.options}
        if user_input is not None:
            return self.async_create_entry(data=_merge(fields, dict(self.config_entry.options), user_input))
        return self.async_show_form(step_id=name, data_schema=_schema(fields, values))

    async def async_step_general(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._section("general", user_input)

    async def async_step_red(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._section("red", user_input)

    async def async_step_consumo(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._section("consumo", user_input)

    async def async_step_solar(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._section("solar", user_input)

    async def async_step_deye(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._section("deye", user_input)

    async def async_step_tarifa(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._section("tarifa", user_input)

    async def async_step_gas(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._section("gas", user_input)

    async def async_step_luces(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._section("luces", user_input)

    async def async_step_clima(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._section("clima", user_input)

    async def async_step_riego(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._section("riego", user_input)

    async def async_step_co2(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._section("co2", user_input)

    async def async_step_problemas(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._section("problemas", user_input)


# ---------------------------------------------------------------------- subentries


class _ItemFlow(ConfigSubentryFlow):
    """Add or edit one string / battery / circuit / zone."""

    FIELDS: Fields = {}
    DEFAULTS: dict[str, Any] = {}

    def _fields(self) -> Fields:
        return {CONF_NAME: (TextSelector(), True), **self.FIELDS}

    def _form(self, step_id: str, values: dict[str, Any]) -> SubentryFlowResult:
        merged = {**self.DEFAULTS, **values}
        schema: dict[Any, Any] = {}
        for key, (selector, required) in self._fields().items():
            current = merged.get(key)
            if required:
                schema[vol.Required(key, default=current) if current is not None else vol.Required(key)] = selector
            else:
                schema[vol.Optional(key, description={"suggested_value": current})] = selector
        return self.async_show_form(step_id=step_id, data_schema=vol.Schema(schema))

    def _clean(self, user_input: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in user_input.items() if v not in (None, "", [])}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        if user_input is not None:
            data = self._clean(user_input)
            return self.async_create_entry(title=str(data[CONF_NAME]), data=data)
        return self._form("user", {})

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        subentry = self._get_reconfigure_subentry()
        if user_input is not None:
            data = self._clean(user_input)
            return self.async_update_and_abort(self._get_entry(), subentry, title=str(data[CONF_NAME]), data=data)
        return self._form("reconfigure", dict(subentry.data))


class StringFlow(_ItemFlow):
    FIELDS: Fields = {
        CONF_POWER: (POWER, True),
        CONF_VOLTAGE: (SENSOR, False),
        CONF_CURRENT: (SENSOR, False),
        CONF_ENERGY: (ENERGY, False),
        CONF_PEAK: (_number(0, 50000, 1, "Wp"), True),
        CONF_GROUP: (TextSelector(), True),
    }
    DEFAULTS = {CONF_PEAK: 0, CONF_GROUP: "A"}


class BatteryFlow(_ItemFlow):
    FIELDS: Fields = {
        CONF_SOC: (SENSOR, True),
        CONF_POWER: (POWER, True),
        CONF_BATTERY_SIGN: (_select([BAT_POSITIVE_DISCHARGE, BAT_POSITIVE_CHARGE], CONF_BATTERY_SIGN), True),
        CONF_CAPACITY: (_number(0, 500, "any", "kWh"), True),
        CONF_VOLTAGE: (SENSOR, False),
        CONF_CURRENT: (SENSOR, False),
        CONF_TEMPERATURE: (_entity("sensor", multiple=True), False),
        CONF_CELLS: (_entity("sensor", multiple=True), False),
        CONF_CELL_LOW: (SENSOR, False),
        CONF_CELL_HIGH: (SENSOR, False),
        CONF_CELL_DIFF: (SENSOR, False),
        CONF_ALARMS: (ANY_STATUS, False),
        CONF_CYCLES: (SENSOR, False),
        CONF_LINK: (_entity("binary_sensor"), False),
        CONF_BANK: (BooleanSelector(), True),
    }
    DEFAULTS = {CONF_BATTERY_SIGN: BAT_POSITIVE_DISCHARGE, CONF_CAPACITY: 5.0, CONF_BANK: True}


class CircuitFlow(_ItemFlow):
    FIELDS: Fields = {
        CONF_POWER: (POWER, True),
        CONF_ENERGY: (ENERGY, False),
        CONF_GROUP: (TextSelector(), True),
        CONF_PARENT: (TextSelector(), False),
        CONF_IN_TOTAL: (BooleanSelector(), True),
        CONF_ICON: (IconSelector(), False),
    }
    DEFAULTS = {CONF_GROUP: "Cuadro", CONF_IN_TOTAL: True}


class ZoneFlow(_ItemFlow):
    FIELDS: Fields = {
        CONF_VALVE: (_entity(["switch", "valve", "input_boolean"]), True),
        CONF_SOIL: (SENSOR, False),
        CONF_MINUTES: (_number(1, 240, 1, "min"), True),
        CONF_MAX_MINUTES: (_number(1, 480, 1, "min"), True),
    }
    DEFAULTS = {CONF_MINUTES: 10, CONF_MAX_MINUTES: 60}
