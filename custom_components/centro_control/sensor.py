"""Sensors for Centro de Control."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfEnergy,
    UnitOfMass,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolume,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import SUB_CIRCUIT, SUB_STRING, SUB_ZONE
from .entity import CentroEntity
from .manager import CentroConfigEntry, CentroManager

EUR = "€"
EUR_KWH = "€/kWh"
W = UnitOfPower.WATT
KWH = UnitOfEnergy.KILO_WATT_HOUR

Value = Callable[[CentroManager], StateType]
Attrs = Callable[[CentroManager], dict[str, Any]]


def _r(value: float | None, digits: int = 1) -> float | None:
    return None if value is None else round(value, digits)


def _live(key: str, digits: int = 0) -> Value:
    return lambda m: _r(m.live.get(key), digits)


def _bucket(metric: str, digits: int = 3) -> Value:
    return lambda m: round(m.counters.get(metric, "hoy"), digits)


def _buckets(metric: str) -> Attrs:
    def attrs(m: CentroManager) -> dict[str, Any]:
        values = m.counters.buckets(metric)
        values["periodo_seleccionado"] = values.get(m.period, 0.0)
        return values

    return attrs


def _insight(key: str) -> Attrs:
    def attrs(m: CentroManager) -> dict[str, Any]:
        out = {bucket: values.get(key) for bucket, values in m.insights.items()}
        out["periodo_seleccionado"] = out.get(m.period)
        return out

    return attrs


def _circuits(m: CentroManager) -> dict[str, Any]:
    load = m.live.get("load_w") or 0.0
    items = []
    for cid, c in m.live.get("circuits", {}).items():
        w = c.get("w")
        items.append(
            {
                "id": cid,
                **c,
                "pct": round(100 * w / load, 1) if w is not None and load else None,
                "periodo_kwh": round(m.counters.get(f"circuito_{cid}", m.period), 3),
            }
        )
    items.sort(key=lambda c: -(c["w"] or 0))
    return {"circuitos": items, "no_medido_w": _r(m.live.get("unmeasured_w"), 0)}


def _strings(m: CentroManager) -> dict[str, Any]:
    return {
        "strings": [{"id": sid, **s} for sid, s in m.live.get("strings", {}).items()],
        "pico_wp": m.model.peak_wp,
        "rendimiento_pct": round(100 * (m.live.get("pv_w") or 0) / m.model.peak_wp, 1) if m.model.peak_wp else None,
    }


def _batteries(m: CentroManager) -> dict[str, Any]:
    return {
        "baterias": [{"id": bid, **b} for bid, b in m.live.get("batteries", {}).items()],
        "capacidad_kwh": m.model.capacity_kwh,
    }


def _soc_pair(m: CentroManager) -> dict[str, Any]:
    return {"baterias": [{"nombre": n, "soc": v} for n, v in m.live.get("soc_pair", [])]}


def _problems_attrs(m: CentroManager) -> dict[str, Any]:
    problems = m.problems
    return {
        "lista": problems,
        "total": len(problems),
        "criticos": sum(1 for p in problems if p["nivel"] == "critico"),
        "avisos": sum(1 for p in problems if p["nivel"] == "aviso"),
        "info": sum(1 for p in problems if p["nivel"] == "info"),
        "reconocidos": sum(1 for p in problems if p["reconocido"]),
    }


def _lights_on(m: CentroManager) -> StateType:
    return sum(1 for e in m.light_entities() if (st := m.hass.states.get(e)) and st.state == "on")


def _lights_attrs(m: CentroManager) -> dict[str, Any]:
    on, outdoor = [], 0
    total = m.light_entities()
    for e in total:
        st = m.hass.states.get(e)
        if st and st.state == "on":
            name = str(st.attributes.get("friendly_name", e))
            on.append({"entidad": e, "nombre": name})
            outdoor += m.model.is_outdoor(f"{e} {name}")
    unavailable = sum(1 for e in total if (st := m.hass.states.get(e)) is None or st.state == "unavailable")
    return {"encendidas": on, "total": len(total), "exterior": outdoor, "interior": len(on) - outdoor, "sin_conexion": unavailable}


def _temps(m: CentroManager, entities: list[str], exclude: str | None = None) -> list[tuple[str, str, float]]:
    out = []
    for e in entities:
        if e == exclude:
            continue
        st = m.hass.states.get(e)
        try:
            out.append((e, str(st.attributes.get("friendly_name", e)), float(st.state)))  # type: ignore[union-attr]
        except (AttributeError, TypeError, ValueError):
            continue
    return out


def _avg_temp(m: CentroManager) -> StateType:
    values = _temps(m, m.temperature_entities(), m.model.get("temperatura_exterior"))
    return round(sum(v for *_, v in values) / len(values), 1) if values else None


def _temp_attrs(m: CentroManager) -> dict[str, Any]:
    values = _temps(m, m.temperature_entities(), m.model.get("temperatura_exterior"))
    if not values:
        return {}
    hot = max(values, key=lambda x: x[2])
    cold = min(values, key=lambda x: x[2])
    return {
        "maxima": hot[2],
        "maxima_nombre": hot[1],
        "minima": cold[2],
        "minima_nombre": cold[1],
        "sensores": len(values),
    }


def _avg_humidity(m: CentroManager) -> StateType:
    values = _temps(m, m.humidity_entities())
    return round(sum(v for *_, v in values) / len(values), 0) if values else None


def _bill_attrs(key: str) -> Attrs:
    return lambda m: m.forecast.get(key, {}) if key != "proximas" else {}


def _forecast_attrs(m: CentroManager) -> dict[str, Any]:
    return {**m.forecast.get("fin_periodo", {}), "proximas": m.forecast.get("proximas", [])}


def _co2_emitted(m: CentroManager) -> StateType:
    return round(m.counters.get("co2_red") + m.counters.get("co2_gas"), 2)


def _co2_attrs(m: CentroManager) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for bucket, values in m.insights.items():
        out[bucket] = {k[4:]: v for k, v in values.items() if k.startswith("co2_")}
    out["periodo_seleccionado"] = out.get(m.period)
    out["factor_red_kg_kwh"] = m.live.get("co2_factor")
    return out


def _gas_attrs(m: CentroManager) -> dict[str, Any]:
    out = _buckets("gas_m3")(m)
    factor = m.gas_factor()
    out["kwh"] = {k: round(v * factor, 2) for k, v in out.items() if isinstance(v, float)}
    out["factor_conversion"] = factor
    out["entidades_gas_tur"] = m.gas_entities
    return out


def _history_attrs(m: CentroManager) -> dict[str, Any]:
    return {"dias": m.history_days(), "meses": m.history_months()}


@dataclass(frozen=True, kw_only=True)
class CentroSensorDescription(SensorEntityDescription):
    value: Value
    attrs: Attrs | None = None


def _power(key: str, live: str, icon: str | None = None, **kw: Any) -> CentroSensorDescription:
    return CentroSensorDescription(
        key=key,
        native_unit_of_measurement=W,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value=_live(live),
        icon=icon,
        **kw,
    )


def _energy(key: str, metric: str) -> CentroSensorDescription:
    return CentroSensorDescription(
        key=key,
        native_unit_of_measurement=KWH,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        value=_bucket(metric),
        attrs=_buckets(metric),
    )


def _money(key: str, metric: str) -> CentroSensorDescription:
    return CentroSensorDescription(
        key=key,
        native_unit_of_measurement=EUR,
        device_class=SensorDeviceClass.MONETARY,
        suggested_display_precision=2,
        value=_bucket(metric, 2),
        attrs=_buckets(metric),
    )


MAIN: tuple[CentroSensorDescription, ...] = (
    # ------------------------------------------------------------- live power
    _power("potencia_solar", "pv_w", attrs=_strings),
    _power("potencia_red", "grid_w"),
    _power("potencia_importada", "import_w"),
    _power("potencia_exportada", "export_w"),
    _power("potencia_bateria", "battery_w", attrs=_batteries),
    _power("potencia_consumo", "load_w", attrs=_circuits),
    _power("potencia_no_medida", "unmeasured_w"),
    CentroSensorDescription(
        key="soc_bateria",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        value=_live("soc", 1),
    ),
    CentroSensorDescription(
        key="diferencia_soc",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:scale-unbalanced",
        value=_live("soc_diff", 1),
        attrs=_soc_pair,
    ),
    CentroSensorDescription(
        key="energia_almacenada",
        native_unit_of_measurement=KWH,
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value=_live("battery_kwh", 2),
    ),
    CentroSensorDescription(
        key="autonomia_bateria",
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_class=SensorDeviceClass.DURATION,
        suggested_display_precision=1,
        value=_live("autonomy_h", 1),
    ),
    CentroSensorDescription(
        key="autosuficiencia_ahora",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value=_live("self_sufficiency", 1),
    ),
    CentroSensorDescription(
        key="uso_potencia_contratada",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value=_live("contracted_pct", 1),
        attrs=lambda m: {"contratada_kw": m.live.get("contracted_kw"), "periodo": m.live.get("power_period")},
    ),
    CentroSensorDescription(
        key="precio_actual",
        native_unit_of_measurement=EUR_KWH,
        suggested_display_precision=4,
        value=_live("price", 5),
        attrs=lambda m: {"periodo": m.live.get("energy_period"), "modo": m.tariff.mode},
    ),
    CentroSensorDescription(
        key="precio_excedentes",
        native_unit_of_measurement=EUR_KWH,
        suggested_display_precision=4,
        value=_live("export_price", 5),
    ),
    CentroSensorDescription(
        key="periodo_tarifario",
        device_class=SensorDeviceClass.ENUM,
        options=["P1", "P2", "P3"],
        value=lambda m: m.live.get("energy_period"),
    ),
    # ------------------------------------------------------------- energy (today, buckets in attrs)
    _energy("energia_solar", "solar"),
    _energy("energia_importada", "importada"),
    _energy("energia_exportada", "exportada"),
    _energy("energia_consumo", "consumo"),
    _energy("energia_bateria_carga", "bateria_carga"),
    _energy("energia_bateria_descarga", "bateria_descarga"),
    # ------------------------------------------------------------- money
    _money("coste_energia", "coste_energia"),
    _money("compensacion_excedentes", "compensacion"),
    CentroSensorDescription(
        key="ahorro_solar",
        native_unit_of_measurement=EUR,
        device_class=SensorDeviceClass.MONETARY,
        suggested_display_precision=2,
        value=lambda m: m.insights.get("mes", {}).get("ahorro_eur"),
        attrs=_insight("ahorro_eur"),
    ),
    CentroSensorDescription(
        key="factura_actual",
        native_unit_of_measurement=EUR,
        device_class=SensorDeviceClass.MONETARY,
        suggested_display_precision=2,
        value=lambda m: m.forecast.get("actual", {}).get("total"),
        attrs=_bill_attrs("actual"),
    ),
    CentroSensorDescription(
        key="prevision_factura",
        native_unit_of_measurement=EUR,
        device_class=SensorDeviceClass.MONETARY,
        suggested_display_precision=2,
        value=lambda m: m.forecast.get("fin_periodo", {}).get("total"),
        attrs=_forecast_attrs,
    ),
    CentroSensorDescription(
        key="simulacion_factura",
        native_unit_of_measurement=EUR,
        device_class=SensorDeviceClass.MONETARY,
        suggested_display_precision=2,
        value=lambda m: m.simulation.get("simulada", {}).get("total"),
        attrs=lambda m: m.simulation,
    ),
    # ------------------------------------------------------------- ratios and co2
    CentroSensorDescription(
        key="autoconsumo",
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
        value=lambda m: m.insights.get("hoy", {}).get("autoconsumo_pct"),
        attrs=_insight("autoconsumo_pct"),
    ),
    CentroSensorDescription(
        key="autosuficiencia",
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
        value=lambda m: m.insights.get("hoy", {}).get("autosuficiencia_pct"),
        attrs=_insight("autosuficiencia_pct"),
    ),
    CentroSensorDescription(
        key="co2_evitado",
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        device_class=SensorDeviceClass.WEIGHT,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        value=_bucket("co2_evitado", 3),
        attrs=_co2_attrs,
    ),
    CentroSensorDescription(
        key="co2_emitido",
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        device_class=SensorDeviceClass.WEIGHT,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        value=_co2_emitted,
    ),
    CentroSensorDescription(
        key="consumo_gas",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        device_class=SensorDeviceClass.GAS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=3,
        value=_bucket("gas_m3", 3),
        attrs=_gas_attrs,
    ),
    # ------------------------------------------------------------- house
    CentroSensorDescription(
        key="problemas",
        icon="mdi:alert-decagram",
        state_class=SensorStateClass.MEASUREMENT,
        value=lambda m: sum(1 for p in m.problems if not p["reconocido"]),
        attrs=_problems_attrs,
    ),
    CentroSensorDescription(
        key="luces_encendidas",
        icon="mdi:lightbulb-group",
        state_class=SensorStateClass.MEASUREMENT,
        value=_lights_on,
        attrs=_lights_attrs,
    ),
    CentroSensorDescription(
        key="temperatura_interior",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value=_avg_temp,
        attrs=_temp_attrs,
    ),
    CentroSensorDescription(
        key="humedad_interior",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        value=_avg_humidity,
    ),
    CentroSensorDescription(
        key="historico",
        icon="mdi:chart-timeline-variant",
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda m: len(m.counters.history),
        attrs=_history_attrs,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CentroConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    manager = entry.runtime_data
    async_add_entities(CentroSensor(manager, d) for d in MAIN)
    for sub_id, sub in entry.subentries.items():
        if sub.subentry_type == SUB_STRING:
            async_add_entities([StringEnergy(manager, sub_id, sub.title)], config_subentry_id=sub_id)
        elif sub.subentry_type == SUB_CIRCUIT:
            async_add_entities([CircuitEnergy(manager, sub_id, sub.title)], config_subentry_id=sub_id)
        elif sub.subentry_type == SUB_ZONE:
            async_add_entities([ZoneRemaining(manager, sub_id, sub.title)], config_subentry_id=sub_id)


class CentroSensor(CentroEntity, SensorEntity):
    entity_description: CentroSensorDescription

    def __init__(self, manager: CentroManager, description: CentroSensorDescription) -> None:
        super().__init__(manager, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> StateType:
        return self.entity_description.value(self.coordinator)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.attrs is None:
            return None
        return self.entity_description.attrs(self.coordinator)


class _SubEnergy(CentroEntity, SensorEntity):
    _attr_native_unit_of_measurement = KWH
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = 2
    PREFIX = ""
    KEY = ""
    LIVE = ""
    MODEL = ""

    def __init__(self, manager: CentroManager, sub_id: str, title: str) -> None:
        super().__init__(manager, self.KEY, sub_id, title, self.MODEL)
        self.metric = f"{self.PREFIX}_{sub_id}"

    @property
    def native_value(self) -> StateType:
        return round(self.coordinator.counters.get(self.metric), 3)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        live = self.coordinator.live.get(self.LIVE, {}).get(self.subentry_id, {})
        return {**self.coordinator.counters.buckets(self.metric), **{k: v for k, v in live.items() if k != "nombre"}}


class StringEnergy(_SubEnergy):
    PREFIX, KEY, LIVE, MODEL = "string", "energia_string", "strings", "String fotovoltaico"


class CircuitEnergy(_SubEnergy):
    PREFIX, KEY, LIVE, MODEL = "circuito", "energia_circuito", "circuits", "Circuito"


class ZoneRemaining(CentroEntity, SensorEntity):
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_icon = "mdi:timer-sand"
    _attr_suggested_display_precision = 0

    def __init__(self, manager: CentroManager, sub_id: str, title: str) -> None:
        super().__init__(manager, "riego_restante", sub_id, title, "Zona de riego")

    @property
    def native_value(self) -> StateType:
        return self.coordinator.zone_remaining(self.subentry_id or "")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        m = self.coordinator
        zone = next((z for z in m.model.zones if z.id == self.subentry_id), None)
        last = m.zone_last.get(self.subentry_id or "", {})
        soil = m.hass.states.get(zone.soil) if zone and zone.soil else None
        return {
            "valvula": zone.valve if zone else None,
            "regando": (self.subentry_id or "") in m.zone_runs,
            "ultimo_riego": last.get("fin"),
            "ultimo_riego_minutos": last.get("minutos"),
            "humedad_suelo": soil.state if soil else None,
            "minutos_programados": m.zone_minutes.get(self.subentry_id or ""),
        }
