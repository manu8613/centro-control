"""Live state, energy accounting, problems and irrigation for one Centro de Control."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
import time
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import CALLBACK_TYPE, Event, EventStateChangedData, HomeAssistant, State, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_HISTORY_DAYS,
    CONF_BILLING_DAY,
    CONF_CO2_CAR,
    CONF_CO2_FACTOR,
    CONF_CO2_GAS,
    CONF_CO2_SENSOR,
    CONF_CO2_TREE,
    CONF_CONTRACTED_P1,
    CONF_CONTRACTED_P2,
    CONF_ELECTRICITY_TAX,
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
    CONF_GAS_METER,
    CONF_GRID_EXPORT_ENERGY,
    CONF_GRID_IMPORT_ENERGY,
    CONF_GRID_POWER,
    CONF_LOAD_ENERGY,
    CONF_LOAD_POWER,
    CONF_METER_RENTAL,
    CONF_NOTIFY_LEVEL,
    CONF_NOTIFY_SERVICE,
    CONF_OTHER_FIXED,
    CONF_OUTDOOR_TEMP,
    CONF_POWER_PRICE_P1,
    CONF_POWER_PRICE_P2,
    CONF_PRICE_FLAT,
    CONF_PRICE_MODE,
    CONF_PRICE_P1,
    CONF_PRICE_P2,
    CONF_PRICE_P3,
    CONF_PRICE_SENSOR,
    CONF_PV_ENERGY,
    CONF_PV_POWER,
    CONF_RAIN_SENSOR,
    CONF_SOC_MIN,
    CONF_VAT,
    DOMAIN,
    HISTORY_DAYS,
    LEVELS,
    MAX_INTEGRATION_GAP,
    PERIODS,
    PROBLEMS_TICK,
    SAVE_DELAY,
    STORAGE_MINOR_VERSION,
    STORAGE_VERSION,
    TICK,
)
from .energy import Counters, Integrator, Meter, to_kwh, to_watts
from .insights import summary
from .model import Model
from .problems import Debouncer, Live, Problem, evaluate
from .tariff import (
    Scenario,
    Tariff,
    current_bill,
    energy_period,
    forecast_current,
    forecast_next,
    power_period,
    simulate,
)

_LOGGER = logging.getLogger(__name__)

type CentroConfigEntry = ConfigEntry[CentroManager]

BAD = (STATE_UNAVAILABLE, STATE_UNKNOWN, None, "")
ON_STATES = ("on", "open", "opening")
GAS_TUR_KEYS = (
    "lectura",
    "consumo_hoy",
    "consumo_mes",
    "consumo_factura",
    "caudal",
    "coste_hoy",
    "coste_mes",
    "factura",
    "prevision_factura",
    "precio_kwh",
    "precio_m3",
    "factor_conversion",
)
WEATHER_PLATFORMS = frozenset(
    {
        "accuweather",
        "aemet",
        "bom",
        "buienradar",
        "environment_canada",
        "ipma",
        "met",
        "met_eireann",
        "meteo_france",
        "meteoclimatic",
        "metoffice",
        "nws",
        "open_meteo",
        "openweathermap",
        "pirateweather",
        "smhi",
        "tomorrowio",
        "weatherflow",
        "weatherflow_cloud",
        "weatherkit",
        "google_weather",
        "meteoalarm",
        "pvpc_hourly_pricing",
        "forecast_solar",
        "solcast_solar",
    }
)
SIM_DEFAULTS: dict[str, float] = {
    "sim_potencia_p1": -1.0,  # -1 = same as the contract
    "sim_potencia_p2": -1.0,
    "sim_consumo": 0.0,
    "sim_precio": 0.0,
    "sim_paneles": 0.0,
    "sim_bateria": 0.0,
    "sim_excedentes": -1.0,
}


def _float(state: State | None) -> float | None:
    if state is None or state.state in BAD:
        return None
    try:
        return float(state.state)
    except (TypeError, ValueError):
        return None


class CentroManager(DataUpdateCoordinator[None]):
    """Owns every figure shown by the entities and the panel."""

    def __init__(self, hass: HomeAssistant, entry: CentroConfigEntry) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=entry.title, update_interval=None)
        self.model = Model.build(
            entry.data,
            entry.options,
            ((sid, sub.subentry_type, sub.data) for sid, sub in entry.subentries.items()),
        )
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}", minor_version=STORAGE_MINOR_VERSION)
        self.counters = Counters(billing_day=int(self.model.num(CONF_BILLING_DAY, 1)), history_days=HISTORY_DAYS)
        self._meters: dict[str, Meter] = {}
        self._integrators: dict[str, Integrator] = {}
        self._meter_sources: dict[str, str] = {}  # entity -> metric
        self._unsubs: list[CALLBACK_TYPE] = []
        self._zone_timers: dict[str, CALLBACK_TYPE] = {}
        self.debouncer = Debouncer()
        self.problems: list[dict[str, Any]] = []
        self.acknowledged: set[str] = set()
        self.notified: set[str] = set()
        self.zone_runs: dict[str, dict[str, float]] = {}  # zone id -> {start, end}
        self.zone_last: dict[str, dict[str, Any]] = {}
        self.zone_minutes: dict[str, float] = {z.id: z.minutes for z in self.model.zones}
        self.skip_rain = True
        self.period = "hoy"
        self.sim: dict[str, float] = dict(SIM_DEFAULTS)
        self.live: dict[str, Any] = {}
        self.forecast: dict[str, Any] = {}
        self.simulation: dict[str, Any] = {}
        self.insights: dict[str, Any] = {}
        self.gas_entities: dict[str, str] = {}
        self._forecast_at = 0.0
        self._forced_close: dict[str, float] = {}
        self.imported = False

    # ================================================================ setup
    @property
    def tariff(self) -> Tariff:
        m = self.model
        return Tariff(
            mode=str(m.get(CONF_PRICE_MODE)),
            p1=m.num(CONF_PRICE_P1),
            p2=m.num(CONF_PRICE_P2),
            p3=m.num(CONF_PRICE_P3),
            flat=m.num(CONF_PRICE_FLAT),
            export_mode=str(m.get(CONF_EXPORT_MODE)),
            export_price=m.num(CONF_EXPORT_PRICE),
            export_cap=bool(m.get(CONF_EXPORT_CAP)),
            power_p1_day=m.num(CONF_POWER_PRICE_P1),
            power_p2_day=m.num(CONF_POWER_PRICE_P2),
            kw_p1=m.num(CONF_CONTRACTED_P1),
            kw_p2=m.num(CONF_CONTRACTED_P2),
            tax_pct=m.num(CONF_ELECTRICITY_TAX),
            vat_pct=m.num(CONF_VAT),
            rental_day=m.num(CONF_METER_RENTAL),
            other_day=m.num(CONF_OTHER_FIXED),
        )

    async def async_load(self) -> None:
        data = await self._store.async_load() or {}
        billing = int(self.model.num(CONF_BILLING_DAY, 1))
        self.counters = Counters.from_dict(data.get("counters"), billing, HISTORY_DAYS)
        self.counters.set_billing_day(billing, dt_util.now().date())
        self._meters = {k: Meter.from_dict(v) for k, v in data.get("meters", {}).items()}
        self.acknowledged = set(data.get("acknowledged", []))
        self.zone_runs = {k: v for k, v in data.get("zone_runs", {}).items() if k in self.zone_minutes}
        self.zone_last = data.get("zone_last", {})
        self.zone_minutes.update({k: float(v) for k, v in data.get("zone_minutes", {}).items() if k in self.zone_minutes})
        self.skip_rain = bool(data.get("skip_rain", True))
        self.period = data.get("period", "hoy") if data.get("period") in PERIODS else "hoy"
        self.sim.update({k: float(v) for k, v in data.get("sim", {}).items() if k in SIM_DEFAULTS})
        self.imported = bool(data.get("imported", False))
        self.gas_entities = self._find_gas_tur()

    def _data_to_save(self) -> dict[str, Any]:
        return {
            "counters": self.counters.as_dict(),
            "meters": {k: v.as_dict() for k, v in self._meters.items()},
            "acknowledged": sorted(self.acknowledged),
            "zone_runs": self.zone_runs,
            "zone_last": self.zone_last,
            "zone_minutes": self.zone_minutes,
            "skip_rain": self.skip_rain,
            "period": self.period,
            "sim": self.sim,
            "imported": self.imported,
        }

    @callback
    def schedule_save(self) -> None:
        self._store.async_delay_save(self._data_to_save, SAVE_DELAY)

    async def async_flush(self) -> None:
        await self._store.async_save(self._data_to_save())

    async def async_remove_store(self) -> None:
        await self._store.async_remove()

    def _find_gas_tur(self) -> dict[str, str]:
        """Entities of the Gas TUR integration, if it is installed and auto mode is on."""
        found: dict[str, str] = {}
        m = self.model
        manual = {
            "lectura": m.get(CONF_GAS_METER),
            "coste_hoy": m.get(CONF_GAS_COST_TODAY),
            "coste_mes": m.get(CONF_GAS_COST_MONTH),
            "factura": m.get(CONF_GAS_BILL),
            "caudal": m.get(CONF_GAS_FLOW),
        }
        if m.get(CONF_GAS_AUTO):
            registry = er.async_get(self.hass)
            for entry in registry.entities.values():
                if entry.platform != "gas_tur" or not entry.unique_id:
                    continue
                for key in GAS_TUR_KEYS:
                    if entry.unique_id.endswith(f"_{key}") and key not in found:
                        found[key] = entry.entity_id
        found.update({k: v for k, v in manual.items() if v})
        return found

    @callback
    def async_start(self) -> None:
        m = self.model
        meters: dict[str, str] = {}
        if m.get(CONF_PV_ENERGY):
            meters[m.get(CONF_PV_ENERGY)] = "solar"
        if m.get(CONF_GRID_IMPORT_ENERGY):
            meters[m.get(CONF_GRID_IMPORT_ENERGY)] = "importada"
        if m.get(CONF_GRID_EXPORT_ENERGY):
            meters[m.get(CONF_GRID_EXPORT_ENERGY)] = "exportada"
        if m.get(CONF_LOAD_ENERGY):
            meters[m.get(CONF_LOAD_ENERGY)] = "consumo"
        for s in m.strings:
            if s.energy:
                meters[s.energy] = s.metric
        for c in m.circuits:
            if c.energy:
                meters[c.energy] = c.metric
        if gas := self.gas_entities.get("lectura"):
            meters[gas] = "gas_m3"
        self._meter_sources = meters
        if meters:
            self._unsubs.append(async_track_state_change_event(self.hass, list(meters), self._on_meter))
        valves = [z.valve for z in m.zones]
        if valves:
            self._unsubs.append(async_track_state_change_event(self.hass, valves, self._on_valve))
        self._unsubs.append(async_track_time_interval(self.hass, self._tick, TICK))
        self._unsubs.append(async_track_time_interval(self.hass, self._problems_tick, PROBLEMS_TICK))
        self._restore_zone_runs()
        self._tick(dt_util.now())
        self._problems_tick(dt_util.now())

    @callback
    def async_stop(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        for unsub in self._zone_timers.values():
            unsub()
        self._zone_timers.clear()

    async def _async_update_data(self) -> None:
        self._tick(dt_util.now())

    # ================================================================ readings
    def _num(self, entity: str | None) -> float | None:
        return _float(self.hass.states.get(entity)) if entity else None

    def _watts(self, entity: str | None) -> float | None:
        state = self.hass.states.get(entity) if entity else None
        value = _float(state)
        if value is None or state is None:
            return None
        return to_watts(value, state.attributes.get("unit_of_measurement"))

    def _price_from(self, entity: str | None) -> float | None:
        state = self.hass.states.get(entity) if entity else None
        value = _float(state)
        if value is None or state is None:
            return None
        unit = str(state.attributes.get("unit_of_measurement") or "").lower()
        return value / 1000 if "mwh" in unit else value

    def price_now(self, now: datetime) -> float:
        tariff = self.tariff
        price = tariff.energy_price(now, self._price_from(self.model.get(CONF_PRICE_SENSOR)))
        return price if price is not None else tariff.typical_price()

    def export_price_now(self) -> float:
        return self.tariff.export_price_now(self._price_from(self.model.get(CONF_EXPORT_SENSOR)))

    def co2_factor_now(self) -> float:
        """kg CO2 per kWh of grid electricity (live sensor in g/kWh if configured)."""
        live = self._num(self.model.get(CONF_CO2_SENSOR))
        if live is not None and live >= 0:
            return live / 1000
        return self.model.num(CONF_CO2_FACTOR, 0.102)

    def gas_factor(self) -> float:
        auto = self._num(self.gas_entities.get("factor_conversion"))
        return auto if auto and auto > 0 else self.model.num(CONF_GAS_FACTOR, 11.0)

    # ================================================================ accounting
    def _add(self, metric: str, amount: float, now: datetime) -> None:
        if amount <= 0:
            return
        day = now.date()
        c = self.counters
        c.add(metric, amount, day)
        if metric == "importada":
            c.add("coste_energia", amount * self.price_now(now), day)
            c.add(f"importada_{energy_period(now).lower()}", amount, day)
            c.add("co2_red", amount * self.co2_factor_now(), day)
        elif metric == "exportada":
            c.add("compensacion", amount * self.export_price_now(), day)
        elif metric == "solar":
            c.add("co2_evitado", amount * self.co2_factor_now(), day)
        elif metric == "gas_m3":
            c.add("co2_gas", amount * self.gas_factor() * self.model.num(CONF_CO2_GAS, 0.182), day)

    def _integrate(self, metric: str, watts: float | None, ts: float, now: datetime) -> None:
        integrator = self._integrators.setdefault(metric, Integrator(max_gap=MAX_INTEGRATION_GAP))
        self._add(metric, integrator.sample(watts, ts), now)

    @callback
    def _on_meter(self, event: Event[EventStateChangedData]) -> None:
        entity = event.data["entity_id"]
        metric = self._meter_sources.get(entity)
        state = event.data["new_state"]
        value = _float(state)
        if metric is None or value is None or state is None:
            return
        unit = state.attributes.get("unit_of_measurement")
        amount = value if metric == "gas_m3" else to_kwh(value, unit)
        meter = self._meters.setdefault(entity, Meter(max_kw=60.0 if metric != "gas_m3" else 10.0))
        self._add(metric, meter.update(amount, time.time()), dt_util.now())
        self.schedule_save()

    # ================================================================ tick
    @callback
    def _tick(self, now: datetime) -> None:
        m = self.model
        ts = time.time()
        if self.counters.roll(now.date()):
            self.schedule_save()
        metered = set(self._meter_sources.values())

        # ---------------- strings and solar
        strings: dict[str, dict[str, Any]] = {}
        for s in m.strings:
            w = self._watts(s.power)
            strings[s.id] = {
                "nombre": s.name,
                "w": w,
                "v": self._num(s.voltage),
                "a": self._num(s.current),
                "wp": s.peak_wp,
                "pct": round(100 * w / s.peak_wp, 1) if w is not None and s.peak_wp else None,
                "grupo": s.group,
                "kwh_hoy": round(self.counters.get(s.metric), 3),
            }
            if s.metric not in metered:
                self._integrate(s.metric, w, ts, now)
        pv = self._watts(m.get(CONF_PV_POWER))
        if pv is None and strings:
            values = [v["w"] for v in strings.values() if v["w"] is not None]
            pv = sum(values) if values else None
        pv = max(pv, 0.0) if pv is not None else None

        # ---------------- grid (+ import)
        grid = self._watts(m.get(CONF_GRID_POWER))
        if grid is not None and m.grid_inverted:
            grid = -grid
        imp = max(grid, 0.0) if grid is not None else None
        exp = max(-grid, 0.0) if grid is not None else None

        # ---------------- batteries (+ discharge)
        batteries: dict[str, dict[str, Any]] = {}
        bat_total: float | None = None
        soc_weight = soc_sum = 0.0
        stored = 0.0
        for b in m.batteries:
            w = self._watts(b.power)
            if w is not None and b.positive_charge:
                w = -w
            soc = self._num(b.soc)
            batteries[b.id] = {"nombre": b.name, "w": w, "soc": soc, "kwh": b.capacity_kwh}
            if w is not None:
                bat_total = (bat_total or 0.0) + w
            if soc is not None:
                weight = b.capacity_kwh or 1.0
                soc_weight += weight
                soc_sum += soc * weight
                stored += b.capacity_kwh * soc / 100
        soc_avg = soc_sum / soc_weight if soc_weight else None

        # ---------------- load
        load = self._watts(m.get(CONF_LOAD_POWER))
        if load is None and (pv is not None or grid is not None):
            load = max((pv or 0.0) + (grid or 0.0) + (bat_total or 0.0), 0.0)

        # ---------------- circuits
        circuits: dict[str, dict[str, Any]] = {}
        in_total = 0.0
        any_circuit = False
        for c in m.circuits:
            w = self._watts(c.power)
            circuits[c.id] = {
                "nombre": c.name,
                "w": w,
                "grupo": c.group,
                "padre": c.parent,
                "icono": c.icon,
                "kwh_hoy": round(self.counters.get(c.metric), 3),
                "en_total": c.in_total,
            }
            if w is not None and c.in_total:
                in_total += w
                any_circuit = True
            if c.metric not in metered:
                self._integrate(c.metric, w, ts, now)

        # ---------------- integrate the main flows
        if "solar" not in metered:
            self._integrate("solar", pv, ts, now)
        if "importada" not in metered:
            self._integrate("importada", imp, ts, now)
        if "exportada" not in metered:
            self._integrate("exportada", exp, ts, now)
        if "consumo" not in metered:
            self._integrate("consumo", load, ts, now)
        self._integrate("bateria_descarga", max(bat_total, 0.0) if bat_total is not None else None, ts, now)
        self._integrate("bateria_carga", max(-bat_total, 0.0) if bat_total is not None else None, ts, now)

        contracted = m.num(CONF_CONTRACTED_P1 if power_period(now) == "P1" else CONF_CONTRACTED_P2)
        autonomy = None
        if load and load > 50 and m.capacity_kwh:
            reserve = m.capacity_kwh * m.num(CONF_SOC_MIN, 10) / 100
            autonomy = round(max(stored - reserve, 0.0) / (load / 1000), 1)
        self.live = {
            "pv_w": pv,
            "grid_w": grid,
            "import_w": imp,
            "export_w": exp,
            "battery_w": bat_total,
            "soc": round(soc_avg, 1) if soc_avg is not None else None,
            "battery_kwh": round(stored, 2) if m.batteries else None,
            "autonomy_h": autonomy,
            "load_w": load,
            "circuits_w": in_total if any_circuit else None,
            "unmeasured_w": max(load - in_total, 0.0) if load is not None and any_circuit else None,
            "self_sufficiency": round(100 * max(1 - (imp or 0) / load, 0.0), 1) if load else None,
            "contracted_kw": contracted,
            "contracted_pct": round(100 * (imp or 0) / (contracted * 1000), 1) if contracted and imp is not None else None,
            "price": round(self.price_now(now), 5),
            "export_price": round(self.export_price_now(), 5),
            "energy_period": energy_period(now),
            "power_period": power_period(now),
            "co2_factor": round(self.co2_factor_now(), 4),
            "strings": strings,
            "batteries": batteries,
            "circuits": circuits,
        }
        tree, car = self.model.num(CONF_CO2_TREE, 22), self.model.num(CONF_CO2_CAR, 0.12)
        self.insights = summary(self.counters, self.tariff.typical_price(), tree, car)
        if ts - self._forecast_at > 300:
            self._update_forecast(now)
        self._check_zone_limits(now)
        self.async_set_updated_data(None)

    # ================================================================ forecasts
    def scenario(self) -> Scenario:
        s = self.sim
        return Scenario(
            consumption_pct=s["sim_consumo"],
            price_pct=s["sim_precio"],
            extra_wp=s["sim_paneles"],
            kw_p1=None if s["sim_potencia_p1"] < 0 else s["sim_potencia_p1"],
            kw_p2=None if s["sim_potencia_p2"] < 0 else s["sim_potencia_p2"],
            export_price=None if s["sim_excedentes"] < 0 else s["sim_excedentes"],
            extra_battery_kwh=s["sim_bateria"],
        )

    def _update_forecast(self, now: datetime) -> None:
        self._forecast_at = time.time()
        tariff = self.tariff
        today = now.date()
        fraction = (now.hour * 3600 + now.minute * 60) / 86400
        try:
            bill = current_bill(self.counters, tariff, today)
            end = forecast_current(self.counters, tariff, today, fraction)
            self.forecast = {
                "actual": bill.as_dict(tariff),
                "fin_periodo": end.as_dict(tariff),
                "proximas": forecast_next(self.counters, tariff, today, self.model.peak_wp, 3),
            }
            self.simulation = simulate(self.counters, tariff, today, self.model.peak_wp, self.scenario())
        except Exception:  # noqa: BLE001 - a forecast must never break the live data
            _LOGGER.exception("No se pudo calcular la previsión de la factura")

    @callback
    def set_sim(self, key: str, value: float) -> None:
        self.sim[key] = value
        self._forecast_at = 0
        self.schedule_save()
        self._tick(dt_util.now())

    @callback
    def set_period(self, value: str) -> None:
        self.period = value
        self.schedule_save()
        self.async_set_updated_data(None)

    # ================================================================ history attrs
    def history_days(self) -> list[dict[str, Any]]:
        today = dt_util.now().date()
        out = []
        for offset in range(ATTR_HISTORY_DAYS, 0, -1):
            day = today - timedelta(days=offset)
            rec = self.counters.history.get(day.isoformat(), {})
            out.append(
                {
                    "fecha": day.isoformat(),
                    "solar": round(rec.get("solar", 0.0), 2),
                    "importada": round(rec.get("importada", 0.0), 2),
                    "exportada": round(rec.get("exportada", 0.0), 2),
                    "consumo": round(rec.get("consumo", 0.0), 2),
                    "coste": round(rec.get("coste_energia", 0.0), 2),
                    "compensacion": round(rec.get("compensacion", 0.0), 2),
                    "co2_evitado": round(rec.get("co2_evitado", 0.0), 2),
                    "gas_m3": round(rec.get("gas_m3", 0.0), 3),
                }
            )
        return out

    def history_months(self, count: int = 24) -> list[dict[str, Any]]:
        today = dt_util.now().date()
        metrics = (
            "solar",
            "importada",
            "exportada",
            "consumo",
            "coste_energia",
            "compensacion",
            "co2_evitado",
            "co2_red",
            "co2_gas",
            "gas_m3",
        )
        series = {metric: dict(self.counters.months(metric, count, today)) for metric in metrics}
        months = list(series["solar"])
        return [{"mes": key, **{m: round(series[m][key], 2) for m in metrics}} for key in months]

    # ================================================================ problems
    def _live_for_problems(self, now: datetime) -> Live:
        live = self.live
        sun = self.hass.states.get("sun.sun")
        is_day = sun.state == "above_horizon" if sun else 8 <= now.hour < 20
        rain = self.hass.states.get(self.model.get(CONF_RAIN_SENSOR)) if self.model.get(CONF_RAIN_SENSOR) else None
        return Live(
            pv_w=live.get("pv_w"),
            load_w=live.get("load_w"),
            grid_w=live.get("grid_w"),
            battery_w=live.get("battery_w"),
            soc=live.get("soc"),
            circuits_w=live.get("circuits_w"),
            contracted_kw=live.get("contracted_kw") or 0.0,
            is_day=is_day,
            raining=self.is_raining(rain),
            zones_open=self.zones_open(now),
            temperatures=tuple(self.temperature_entities()),
            humidities=tuple(self.humidity_entities()),
            outdoor=self.model.get(CONF_OUTDOOR_TEMP),
            skip=frozenset(self._skip_device_checks()),
        )

    def _skip_device_checks(self) -> set[str]:
        """Phones and diagnostic entities are not 'devices with a battery to replace'."""
        registry = er.async_get(self.hass)
        out = set()
        for st in self.hass.states.async_all("sensor"):
            if st.attributes.get("device_class") != "battery":
                continue
            entry = registry.async_get(st.entity_id)
            if entry is not None and (entry.platform == "mobile_app" or entry.disabled_by is not None or entry.hidden_by is not None):
                out.add(st.entity_id)
        return out

    @staticmethod
    def is_raining(state: State | None) -> bool:
        if state is None or state.state in BAD:
            return False
        if state.state in ("on", "rain", "raining", "wet", "lluvia", "rainy", "pouring"):
            return True
        try:
            return float(state.state) > 0
        except ValueError:
            return False

    def raining(self) -> bool:
        entity = self.model.get(CONF_RAIN_SENSOR)
        return self.is_raining(self.hass.states.get(entity)) if entity else False

    @callback
    def _problems_tick(self, now: datetime) -> None:
        try:
            found = evaluate(self.model, self.hass.states.get, self.hass.states.async_all(), self._live_for_problems(now), now)
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Error revisando problemas")
            return
        active = self.debouncer.update(found, now)
        ids = {p.id for p, _ in active}
        self.acknowledged &= ids
        self.notified &= ids
        self.problems = [self._problem_dict(p, since) for p, since in active]
        self._notify([p for p, _ in active])
        self.async_set_updated_data(None)

    def _problem_dict(self, p: Problem, since: datetime) -> dict[str, Any]:
        return {
            "id": p.id,
            "nivel": p.level,
            "area": p.area,
            "titulo": p.title,
            "detalle": p.detail,
            "entidad": p.entity,
            "desde": since.isoformat(timespec="minutes"),
            "reconocido": p.id in self.acknowledged,
        }

    def _notify(self, problems: list[Problem]) -> None:
        service = str(self.model.get(CONF_NOTIFY_SERVICE) or "").strip()
        if not service:
            return
        level = str(self.model.get(CONF_NOTIFY_LEVEL) or "critico")
        limit = LEVELS.index(level) if level in LEVELS else 0
        for p in problems:
            if p.id in self.notified or p.id in self.acknowledged or LEVELS.index(p.level) > limit:
                continue
            self.notified.add(p.id)
            title = f"{self.config_entry.title}: {p.title}"
            self.hass.bus.async_fire(f"{DOMAIN}_problema", {"id": p.id, "nivel": p.level, "titulo": p.title, "detalle": p.detail})
            if service in ("persistent_notification", "notify.persistent_notification"):
                persistent_notification.async_create(self.hass, p.detail, title=title, notification_id=f"{DOMAIN}_{p.id}")
                continue
            domain, _, name = service.partition(".")
            if not name:
                domain, name = "notify", domain
            self.hass.async_create_task(
                self.hass.services.async_call(domain, name, {"title": title, "message": p.detail}, blocking=False),
                f"{DOMAIN} notify",
            )

    @callback
    def acknowledge(self) -> None:
        self.acknowledged = {p["id"] for p in self.problems}
        for p in self.problems:
            p["reconocido"] = True
        self.schedule_save()
        self.async_set_updated_data(None)

    # ================================================================ lights / climate lists
    def _hidden(self, entity_id: str) -> bool:
        """Diagnostic, hidden or leftover entities are not shown automatically."""
        entry = er.async_get(self.hass).async_get(entity_id)
        if entry is not None and (entry.entity_category is not None or entry.hidden_by is not None or entry.disabled_by is not None):
            return True
        state = self.hass.states.get(entity_id)
        return bool(state and state.attributes.get("restored"))

    def light_entities(self) -> list[str]:
        chosen = self.model.lights()
        if chosen:
            return chosen
        excluded = self.model.lights_excluded()
        return sorted(e for e in self.hass.states.async_entity_ids("light") if e not in excluded and not self._hidden(e))

    def climate_entities(self) -> list[str]:
        chosen = self.model.climates()
        return chosen or sorted(e for e in self.hass.states.async_entity_ids("climate") if not self._hidden(e))

    def _auto_class(self, device_class: str) -> list[str]:
        used = self.model.energy_entities()
        registry = er.async_get(self.hass)
        out = []
        for st in self.hass.states.async_all("sensor"):
            if st.attributes.get("device_class") != device_class or st.entity_id in used or self._hidden(st.entity_id):
                continue
            entry = registry.async_get(st.entity_id)
            if entry is not None and entry.platform in WEATHER_PLATFORMS:
                continue  # weather services: forecasts are not rooms
            if self.model.temp_excluded(f"{st.entity_id} {st.attributes.get('friendly_name', '')}"):
                continue
            out.append(st.entity_id)
        return sorted(out)

    def temperature_entities(self) -> list[str]:
        return self.model.temperatures() or self._auto_class("temperature")

    def humidity_entities(self) -> list[str]:
        return self.model.humidities() or self._auto_class("humidity")

    # ================================================================ irrigation
    def zones_open(self, now: datetime) -> dict[str, float]:
        out = {}
        for z in self.model.zones:
            st = self.hass.states.get(z.valve)
            if st and st.state in ON_STATES:
                out[z.name] = (now - st.last_changed).total_seconds() / 60
        return out

    def zone_remaining(self, zone_id: str) -> float:
        run = self.zone_runs.get(zone_id)
        if not run:
            return 0.0
        return max(round((run["end"] - time.time()) / 60, 1), 0.0)

    async def _set_valve(self, entity: str, on: bool) -> None:
        domain = entity.split(".", 1)[0]
        if domain == "valve":
            service = "open_valve" if on else "close_valve"
        elif domain in ("switch", "input_boolean", "light", "fan"):
            service = "turn_on" if on else "turn_off"
        else:
            domain, service = "homeassistant", "turn_on" if on else "turn_off"
        await self.hass.services.async_call(domain, service, {"entity_id": entity}, blocking=True)

    async def async_start_zone(self, zone_id: str, minutes: float | None = None) -> bool:
        zone = next((z for z in self.model.zones if z.id == zone_id or z.name == zone_id), None)
        if zone is None:
            return False
        if self.skip_rain and self.raining():
            persistent_notification.async_create(
                self.hass,
                f"No riego **{zone.name}**: está lloviendo. Desactiva «Omitir riego si llueve» para forzarlo.",
                title=self.config_entry.title,
                notification_id=f"{DOMAIN}_riego_lluvia",
            )
            return False
        minutes = float(minutes or self.zone_minutes.get(zone.id, zone.minutes))
        minutes = max(1.0, min(minutes, zone.max_minutes))
        await self._set_valve(zone.valve, True)
        start = time.time()
        self.zone_runs[zone.id] = {"start": start, "end": start + minutes * 60}
        self._schedule_zone_stop(zone.id, minutes * 60)
        self.schedule_save()
        self.async_set_updated_data(None)
        return True

    def _schedule_zone_stop(self, zone_id: str, delay: float) -> None:
        if unsub := self._zone_timers.pop(zone_id, None):
            unsub()

        async def _stop(_now: datetime) -> None:
            self._zone_timers.pop(zone_id, None)
            await self.async_stop_zone(zone_id)

        self._zone_timers[zone_id] = async_call_later(self.hass, max(delay, 0), _stop)

    async def async_stop_zone(self, zone_id: str) -> None:
        zone = next((z for z in self.model.zones if z.id == zone_id or z.name == zone_id), None)
        if zone is None:
            return
        if unsub := self._zone_timers.pop(zone.id, None):
            unsub()
        self.zone_runs.pop(zone.id, None)
        try:
            await self._set_valve(zone.valve, False)
        finally:
            self.schedule_save()
            self.async_set_updated_data(None)

    async def async_stop_all(self) -> None:
        for z in self.model.zones:
            await self.async_stop_zone(z.id)

    def _restore_zone_runs(self) -> None:
        now = time.time()
        for zone_id, run in list(self.zone_runs.items()):
            self._schedule_zone_stop(zone_id, run["end"] - now)

    def _check_zone_limits(self, now: datetime) -> None:
        for z in self.model.zones:
            st = self.hass.states.get(z.valve)
            if st and st.state in ON_STATES and (now - st.last_changed).total_seconds() > z.max_minutes * 60 + 30:
                last_try = self._forced_close.get(z.id, 0.0)
                if z.id not in self._zone_timers and time.time() - last_try > 300:
                    _LOGGER.warning("Cerrando %s: lleva más de %s min abierta", z.valve, z.max_minutes)
                    self._forced_close[z.id] = time.time()
                    self._schedule_zone_stop(z.id, 0)

    @callback
    def _on_valve(self, event: Event[EventStateChangedData]) -> None:
        old, new = event.data["old_state"], event.data["new_state"]
        if old is None or new is None:
            return
        zone = next((z for z in self.model.zones if z.valve == event.data["entity_id"]), None)
        if zone is None:
            return
        if old.state in ON_STATES and new.state not in ON_STATES:
            minutes = (new.last_changed - old.last_changed).total_seconds() / 60
            self.zone_last[zone.id] = {"fin": new.last_changed.isoformat(timespec="minutes"), "minutos": round(minutes, 1)}
            self.zone_runs.pop(zone.id, None)
            if unsub := self._zone_timers.pop(zone.id, None):
                unsub()
            self.schedule_save()
        self.async_set_updated_data(None)

    @callback
    def set_zone_minutes(self, zone_id: str, minutes: float) -> None:
        self.zone_minutes[zone_id] = minutes
        self.schedule_save()
        self.async_set_updated_data(None)

    @callback
    def set_skip_rain(self, value: bool) -> None:
        self.skip_rain = value
        self.schedule_save()
        self.async_set_updated_data(None)

    # ================================================================ import
    def _history_sources(self) -> tuple[dict[str, str], dict[str, str]]:
        """Statistics to import: metric -> energy meter, metric -> power sensor."""
        meters = {metric: entity for entity, metric in self._meter_sources.items()}
        m = self.model
        powers: dict[str, str] = {}
        if "solar" not in meters and m.get(CONF_PV_POWER):
            powers["solar"] = m.get(CONF_PV_POWER)
        if "consumo" not in meters and m.get(CONF_LOAD_POWER):
            powers["consumo"] = m.get(CONF_LOAD_POWER)
        for s in m.strings:
            if s.metric not in meters:
                powers[s.metric] = s.power
        for c in m.circuits:
            if c.metric not in meters:
                powers[c.metric] = c.power
        return meters, powers

    async def async_import_history(self, days: int = 730) -> int:
        """Fill the daily history with what the recorder already knows."""
        from homeassistant.components.recorder import get_instance
        from homeassistant.components.recorder.statistics import statistics_during_period

        if "recorder" not in self.hass.config.components:
            return 0
        meters, powers = self._history_sources()
        if not meters and not powers:
            return 0
        now = dt_util.now()
        start = dt_util.start_of_local_day(now) - timedelta(days=days)
        end = dt_util.start_of_local_day(now)
        recorder = get_instance(self.hass)
        records: dict[str, dict[str, float]] = {}

        def day_of(ts: float) -> str:
            return dt_util.as_local(dt_util.utc_from_timestamp(ts)).date().isoformat()

        if meters:
            energy = {e for metric, e in meters.items() if metric != "gas_m3"}
            for ids, units in ((energy, {"energy": "kWh"}), ({meters["gas_m3"]} if "gas_m3" in meters else set(), {"volume": "m³"})):
                if not ids:
                    continue
                stats = await recorder.async_add_executor_job(
                    statistics_during_period, self.hass, start, end, ids, "hour", units, {"change"}
                )
                for metric, entity in meters.items():
                    for row in stats.get(entity, []):
                        change = row.get("change")
                        if change and 0 < change < 60:
                            rec = records.setdefault(day_of(row["start"]), {})
                            rec[metric] = rec.get(metric, 0.0) + change
        if powers:
            stats = await recorder.async_add_executor_job(
                statistics_during_period, self.hass, start, end, set(powers.values()), "hour", {"power": "W"}, {"mean"}
            )
            for metric, entity in powers.items():
                for row in stats.get(entity, []):
                    mean = row.get("mean")
                    if mean is not None and mean > 0:
                        rec = records.setdefault(day_of(row["start"]), {})
                        rec[metric] = rec.get(metric, 0.0) + mean / 1000  # one hour at mean W
        tariff = self.tariff
        co2 = self.model.num(CONF_CO2_FACTOR, 0.102)
        for rec in records.values():
            if "importada" in rec:
                rec["coste_energia"] = rec["importada"] * tariff.typical_price()
                rec["co2_red"] = rec["importada"] * co2
            if "exportada" in rec:
                rec["compensacion"] = rec["exportada"] * tariff.export_price_now(None)
            if "solar" in rec:
                rec["co2_evitado"] = rec["solar"] * co2
            if "gas_m3" in rec:
                rec["co2_gas"] = rec["gas_m3"] * self.gas_factor() * self.model.num(CONF_CO2_GAS, 0.182)
        added = self.counters.import_days(records, now.date())
        self.imported = True
        self._forecast_at = 0
        await self.async_flush()
        self._tick(dt_util.now())
        return added

    # ================================================================ maintenance
    @callback
    def reset_counters(self) -> None:
        """Forget every accumulated figure (keeps the configuration)."""
        self.counters = Counters(billing_day=self.counters.billing_day, history_days=HISTORY_DAYS)
        self._meters.clear()
        self._integrators.clear()
        self.schedule_save()
        self._tick(dt_util.now())


def bucket_values(manager: CentroManager, metric: str) -> dict[str, float]:
    return manager.counters.buckets(metric)


__all__: list[str] = ["CentroConfigEntry", "CentroManager", "bucket_values"]
