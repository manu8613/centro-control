"""Detection of problems in the installation (pure Python).

``evaluate`` looks at the current states and returns every condition that is
wrong right now; ``Debouncer`` only reports the ones that have lasted long
enough, so a passing cloud or a one-off reading does not raise an alarm.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import datetime
from statistics import median
from typing import Any, Protocol

from .const import (
    CONF_BATTERY_TEMP_MAX,
    CONF_CELL_DELTA_CRIT,
    CONF_CELL_DELTA_WARN,
    CONF_CELL_MAX,
    CONF_CELL_MIN,
    CONF_CHECK_DEVICE_BATTERIES,
    CONF_CHECK_GRID_WITH_BATTERY,
    CONF_CHECK_SAFETY,
    CONF_DEVICE_BATTERY_MIN,
    CONF_GAS_FLOW,
    CONF_GAS_FLOW_HOURS,
    CONF_GRID_FREQUENCY,
    CONF_GRID_VOLTAGE,
    CONF_HUMIDITY_MAX,
    CONF_INV_ALARM,
    CONF_INV_FAULT,
    CONF_INV_STATUS,
    CONF_INV_TEMP,
    CONF_INV_TEMP2,
    CONF_INV_TEMP_CRIT,
    CONF_INV_TEMP_WARN,
    CONF_SOC_MIN,
    CONF_SOIL_MIN,
    CONF_STRING_TOLERANCE,
    CONF_TEMP_MAX,
    CONF_TEMP_MIN,
    CONF_UNMEASURED_MAX,
    CONF_VOLTAGE_MAX,
    CONF_VOLTAGE_MIN,
)
from .model import Model, slug

LEVEL_ORDER = {"critico": 0, "aviso": 1, "info": 2}
BAD_STATES = ("unavailable", "unknown")
OK_TEXT = {
    "",
    "0",
    "0.0",
    "ok",
    "normal",
    "none",
    "no",
    "off",
    "false",
    "sin alarmas",
    "sin fallos",
    "no fault",
    "no alarm",
    "standby",
    "running",
    "en marcha",
    "funcionando",
    "self-use",
    "normal operation",
}
BAD_STATUS_WORDS = ("fault", "fallo", "error", "alarm", "avería", "averia", "falla")
SAFETY_CLASSES = {
    "moisture": "Fuga de agua",
    "smoke": "Humo detectado",
    "gas": "Gas detectado",
    "carbon_monoxide": "Monóxido de carbono",
}


class StateLike(Protocol):
    entity_id: str
    state: str
    attributes: dict[str, Any]
    last_changed: datetime


@dataclass(frozen=True)
class Problem:
    id: str
    level: str
    area: str
    title: str
    detail: str
    entity: str | None = None
    delay: float = 0.0  # seconds it must last before it is shown


@dataclass
class Live:
    """Live values the manager already computed."""

    pv_w: float | None = None
    load_w: float | None = None
    grid_w: float | None = None  # + import
    battery_w: float | None = None  # + discharge
    soc: float | None = None
    circuits_w: float | None = None
    contracted_kw: float = 0.0
    is_day: bool = True
    raining: bool = False
    zones_open: dict[str, float] = field(default_factory=dict)  # name -> minutes open
    zone_limits: dict[str, float] = field(default_factory=dict)  # name -> max minutes
    lights: tuple[str, ...] = ()
    temperatures: tuple[str, ...] = ()
    humidities: tuple[str, ...] = ()
    outdoor: str | None = None
    skip: frozenset[str] = frozenset()  # entities left out of the house-wide checks


def _num(st: StateLike | None) -> float | None:
    if st is None or st.state in BAD_STATES:
        return None
    try:
        return float(st.state)
    except (TypeError, ValueError):
        return None


def _name(st: StateLike | None, fallback: str) -> str:
    if st is None:
        return fallback
    return str(st.attributes.get("friendly_name") or fallback)


def _fmt(value: float, decimals: int = 1) -> str:
    return f"{value:.{decimals}f}".replace(".", ",")


def evaluate(
    model: Model,
    get: Callable[[str], StateLike | None],
    states: Iterable[StateLike],
    live: Live,
    now: datetime,
) -> list[Problem]:
    out: list[Problem] = []
    out += _availability(model, get)
    out += _grid(model, get, live)
    out += _solar(model, get, live)
    out += _batteries(model, get, live)
    out += _consumption(model, live)
    out += _irrigation(model, get, live)
    out += _climate(model, get, live)
    out += _gas(model, get)
    out += _house(model, states, now, live.skip)
    return sorted(out, key=lambda p: (LEVEL_ORDER.get(p.level, 9), p.area, p.title))


# ---------------------------------------------------------------------- checks


def _availability(model: Model, get: Callable[[str], StateLike | None]) -> list[Problem]:
    out = []
    for area, label, entity in model.sources():
        st = get(entity)
        if st is None:
            out.append(
                Problem(
                    f"falta_{entity}",
                    "aviso",
                    area,
                    f"{label}: la entidad no existe",
                    f"`{entity}` no está en Home Assistant.",
                    entity,
                    300,
                )
            )
        elif st.state in BAD_STATES:
            out.append(
                Problem(
                    f"nodisp_{entity}",
                    "aviso",
                    area,
                    f"{label} no responde",
                    f"`{entity}` está «{st.state}».",
                    entity,
                    600,
                )
            )
    return out


def _grid(model: Model, get: Callable[[str], StateLike | None], live: Live) -> list[Problem]:
    out = []
    if (entity := model.get(CONF_GRID_VOLTAGE)) and (v := _num(get(entity))) is not None and v > 0:
        low, high = model.num(CONF_VOLTAGE_MIN, 207), model.num(CONF_VOLTAGE_MAX, 253)
        if v < low or v > high:
            out.append(
                Problem(
                    "red_tension",
                    "aviso",
                    "Red",
                    "Tensión de red fuera de rango",
                    f"{_fmt(v)} V (permitido {_fmt(low, 0)}–{_fmt(high, 0)} V).",
                    entity,
                    60,
                )
            )
    if (entity := model.get(CONF_GRID_FREQUENCY)) and (f := _num(get(entity))) is not None and f > 0:
        if abs(f - 50.0) > 0.2:
            out.append(Problem("red_frecuencia", "aviso", "Red", "Frecuencia de red anómala", f"{_fmt(f, 2)} Hz.", entity, 30))
    if live.contracted_kw > 0 and live.grid_w is not None:
        use = live.grid_w / (live.contracted_kw * 1000)
        if use >= 0.9:
            out.append(
                Problem(
                    "red_limite",
                    "critico" if use >= 1 else "aviso",
                    "Red",
                    "Cerca del límite de potencia contratada",
                    f"Importando {_fmt(live.grid_w / 1000, 2)} kW de {_fmt(live.contracted_kw, 2)} kW ({use:.0%}).",
                    None,
                    20,
                )
            )
    if (
        model.get(CONF_CHECK_GRID_WITH_BATTERY)
        and model.batteries
        and live.grid_w is not None
        and live.soc is not None
        and live.battery_w is not None
    ):
        floor = model.num(CONF_SOC_MIN, 10) + 30
        if live.grid_w > 300 and live.soc > floor:
            if live.battery_w < -200:
                out.append(
                    Problem(
                        "red_carga_bateria",
                        "info",
                        "Batería",
                        "Cargando la batería desde la red",
                        f"Red {_fmt(live.grid_w, 0)} W mientras la batería carga {_fmt(-live.battery_w, 0)} W (SOC {live.soc:.0f} %).",
                        None,
                        900,
                    )
                )
            elif live.battery_w < 100:
                out.append(
                    Problem(
                        "red_con_bateria",
                        "aviso",
                        "Batería",
                        "Importando de la red con la batería cargada",
                        f"Red {_fmt(live.grid_w, 0)} W con la batería al {live.soc:.0f} % y casi parada. Revisa el modo del inversor.",
                        None,
                        600,
                    )
                )
    return out


def _status_bad(st: StateLike | None) -> str | None:
    """Text of a fault/alarm sensor if it is not in an OK state."""
    if st is None or st.state in BAD_STATES:
        return None
    text = str(st.state).strip()
    low = text.lower()
    if st.entity_id.startswith("binary_sensor."):
        return text if low == "on" else None
    if low in OK_TEXT:
        return None
    try:
        return text if float(text) != 0 else None
    except ValueError:
        pass
    return text


def _solar(model: Model, get: Callable[[str], StateLike | None], live: Live) -> list[Problem]:
    out = []
    warn, crit = model.num(CONF_INV_TEMP_WARN, 60), model.num(CONF_INV_TEMP_CRIT, 70)
    for key, label in ((CONF_INV_TEMP, "Temperatura del inversor"), (CONF_INV_TEMP2, "Temperatura DC del inversor")):
        entity = model.get(key)
        if entity and (t := _num(get(entity))) is not None and t >= warn:
            out.append(
                Problem(
                    f"inv_{key}",
                    "critico" if t >= crit else "aviso",
                    "Solar",
                    f"{label} alta",
                    f"{_fmt(t)} °C (aviso {_fmt(warn, 0)} °C, crítico {_fmt(crit, 0)} °C).",
                    entity,
                    120,
                )
            )
    for key, label in ((CONF_INV_FAULT, "Fallo del inversor"), (CONF_INV_ALARM, "Alarma del inversor")):
        entity = model.get(key)
        if entity and (text := _status_bad(get(entity))):
            out.append(
                Problem(
                    f"inv_{key}", "critico" if key == CONF_INV_FAULT else "aviso", "Solar", label, f"Código/estado: {text}.", entity, 60
                )
            )
    entity = model.get(CONF_INV_STATUS)
    if entity and (st := get(entity)) and st.state not in BAD_STATES:
        if any(word in str(st.state).lower() for word in BAD_STATUS_WORDS):
            out.append(Problem("inv_estado", "critico", "Solar", "El inversor indica un fallo", f"Estado: {st.state}.", entity, 60))

    # Strings: compare specific yield (W/Wp) inside each orientation group.
    peak = model.peak_wp
    total = live.pv_w or 0.0
    if not live.is_day or not model.strings:
        return out
    tolerance = model.num(CONF_STRING_TOLERANCE, 30) / 100
    groups: dict[str, list[tuple[Any, float]]] = {}
    for s in model.strings:
        p = _num(get(s.power))
        if p is None:
            continue
        groups.setdefault(s.group, []).append((s, p))
    for members in groups.values():
        producing = [p for _, p in members if p > 20]
        if len(members) < 2 or not producing:
            continue
        for s, p in members:
            others = [q for t, q in members if t is not s]
            if p <= 5 and max(others) > 150:
                v = _num(get(s.voltage)) if s.voltage else None
                detail = f"0 W mientras los demás strings del grupo {s.group} dan hasta {_fmt(max(others), 0)} W."
                if v is not None:
                    detail += f" Tensión {_fmt(v, 0)} V."
                out.append(Problem(f"string_cero_{s.id}", "critico", "Solar", f"{s.name} sin producción", detail, s.power, 900))
                continue
            if any(x.peak_wp <= 0 for x, _ in members):
                continue
            yields = [q / t.peak_wp for t, q in members]
            ref = median(yields)
            if ref < 0.08:  # under 80 W/kWp: too little light to judge
                continue
            mine = p / s.peak_wp
            if mine < (1 - tolerance) * ref:
                loss = 1 - mine / ref
                out.append(
                    Problem(
                        f"string_bajo_{s.id}",
                        "aviso",
                        "Solar",
                        f"{s.name} rinde menos que el resto",
                        f"{_fmt(p, 0)} W ({_fmt(mine * 1000, 0)} W/kWp) frente a {_fmt(ref * 1000, 0)} W/kWp del grupo {s.group}: un {loss:.0%} menos. Revisa sombras, suciedad o conexiones.",
                        s.power,
                        1800,
                    )
                )
    if peak > 0 and total > 1.05 * peak:
        out.append(
            Problem(
                "solar_pico",
                "info",
                "Solar",
                "Producción por encima de la potencia pico",
                f"{_fmt(total, 0)} W con {_fmt(peak, 0)} Wp configurados: revisa el dato de Wp.",
                None,
                600,
            )
        )
    return out


def _batteries(model: Model, get: Callable[[str], StateLike | None], live: Live) -> list[Problem]:
    out = []
    warn, crit = model.num(CONF_CELL_DELTA_WARN, 0.05), model.num(CONF_CELL_DELTA_CRIT, 0.1)
    vmin, vmax = model.num(CONF_CELL_MIN, 2.9), model.num(CONF_CELL_MAX, 3.6)
    tmax = model.num(CONF_BATTERY_TEMP_MAX, 45)
    soc_min = model.num(CONF_SOC_MIN, 10)
    for b in model.batteries:
        key = slug(b.id)
        soc = _num(get(b.soc))
        if soc is not None and soc <= soc_min:
            out.append(
                Problem(
                    f"bat_soc_{key}",
                    "aviso",
                    "Batería",
                    f"{b.name}: carga muy baja",
                    f"SOC {soc:.0f} % (mínimo {soc_min:.0f} %).",
                    b.soc,
                    300,
                )
            )
        cells = [v for v in (_num(get(c)) for c in b.cells) if v is not None and 1.0 < v < 5.0]
        low = min(cells) if cells else _num(get(b.cell_low)) if b.cell_low else None
        high = max(cells) if cells else _num(get(b.cell_high)) if b.cell_high else None
        delta = (high - low) if cells else None
        if delta is None and b.cell_diff and (diff_state := get(b.cell_diff)) is not None:
            delta = _num(diff_state)
            if delta is not None and (diff_state.attributes.get("unit_of_measurement") == "mV" or delta > 1.0):
                delta /= 1000
        if delta is None and low is not None and high is not None:
            delta = high - low
        if delta is not None and delta >= warn:
            worst = ""
            if cells:
                idx_low = cells.index(low) + 1
                idx_high = cells.index(high) + 1
                worst = f" Celda {idx_low} la más baja ({_fmt(low, 3)} V), celda {idx_high} la más alta ({_fmt(high, 3)} V)."
            out.append(
                Problem(
                    f"bat_delta_{key}",
                    "critico" if delta >= crit else "aviso",
                    "Batería",
                    f"{b.name}: celdas desequilibradas",
                    f"Diferencia {_fmt(delta * 1000, 0)} mV (aviso {_fmt(warn * 1000, 0)} mV).{worst}",
                    b.cell_diff or (b.cells[0] if b.cells else None),
                    600,
                )
            )
        if low is not None and low < vmin:
            out.append(
                Problem(
                    f"bat_vmin_{key}",
                    "critico",
                    "Batería",
                    f"{b.name}: celda por debajo del mínimo",
                    f"{_fmt(low, 3)} V (< {_fmt(vmin, 2)} V).",
                    None,
                    60,
                )
            )
        if high is not None and high > vmax:
            out.append(
                Problem(
                    f"bat_vmax_{key}",
                    "critico",
                    "Batería",
                    f"{b.name}: celda por encima del máximo",
                    f"{_fmt(high, 3)} V (> {_fmt(vmax, 2)} V).",
                    None,
                    60,
                )
            )
        temps = [(t, _num(get(t))) for t in b.temperatures]
        for entity, t in temps:
            if t is not None and t >= tmax:
                out.append(
                    Problem(
                        f"bat_temp_{slug(entity)}",
                        "critico" if t >= tmax + 10 else "aviso",
                        "Batería",
                        f"{b.name}: temperatura alta",
                        f"{_name(get(entity), entity)}: {_fmt(t)} °C.",
                        entity,
                        120,
                    )
                )
            power = _num(get(b.power))
            if t is not None and t < 5 and power is not None:
                charging = power > 50 if b.positive_charge else power < -50
                if charging:
                    out.append(
                        Problem(
                            f"bat_frio_{slug(entity)}",
                            "aviso",
                            "Batería",
                            f"{b.name}: cargando con frío",
                            f"{_fmt(t)} °C: el LiFePO₄ no debe cargar por debajo de 0–5 °C.",
                            entity,
                            300,
                        )
                    )
        if b.alarms and (text := _status_bad(get(b.alarms))):
            out.append(
                Problem(f"bat_alarma_{key}", "critico", "Batería", f"{b.name}: alarma del BMS", f"El BMS indica: {text}.", b.alarms, 30)
            )
    return out


def _consumption(model: Model, live: Live) -> list[Problem]:
    out = []
    if live.load_w is None or live.circuits_w is None or not model.circuits:
        return out
    unmeasured = live.load_w - live.circuits_w
    limit = model.num(CONF_UNMEASURED_MAX, 800)
    if unmeasured > limit and unmeasured > 0.25 * live.load_w:
        out.append(
            Problem(
                "consumo_no_medido",
                "info",
                "Consumo",
                "Mucho consumo sin medir",
                f"{_fmt(unmeasured, 0)} W del total ({_fmt(live.load_w, 0)} W) no los mide ningún circuito.",
                None,
                1800,
            )
        )
    if live.circuits_w > live.load_w * 1.15 + 150:
        out.append(
            Problem(
                "consumo_suma",
                "aviso",
                "Consumo",
                "Los circuitos suman más que el consumo total",
                f"Circuitos {_fmt(live.circuits_w, 0)} W frente a {_fmt(live.load_w, 0)} W totales: el medidor general o algún circuito no mide bien, o un circuito cuelga de otro y falta indicarlo.",
                None,
                900,
            )
        )
    return out


def _irrigation(model: Model, get: Callable[[str], StateLike | None], live: Live) -> list[Problem]:
    out = []
    soil_min = model.num(CONF_SOIL_MIN, 20)
    for z in model.zones:
        minutes = live.zones_open.get(z.name)
        if minutes is not None:
            if minutes > z.max_minutes:
                out.append(
                    Problem(
                        f"riego_largo_{slug(z.id)}",
                        "critico",
                        "Riego",
                        f"{z.name} lleva demasiado tiempo abierto",
                        f"{minutes:.0f} min abierto (máximo {z.max_minutes:.0f}). Posible fuga o válvula atascada.",
                        z.valve,
                        0,
                    )
                )
            if live.raining:
                out.append(
                    Problem(
                        f"riego_lluvia_{slug(z.id)}",
                        "aviso",
                        "Riego",
                        f"Regando {z.name} mientras llueve",
                        "El sensor de lluvia está activo.",
                        z.valve,
                        60,
                    )
                )
        if z.soil and (h := _num(get(z.soil))) is not None and h < soil_min and not live.raining:
            out.append(
                Problem(
                    f"riego_seco_{slug(z.id)}",
                    "info",
                    "Riego",
                    f"Tierra seca en {z.name}",
                    f"Humedad {h:.0f} % (mínimo {soil_min:.0f} %).",
                    z.soil,
                    1800,
                )
            )
    return out


def _climate(model: Model, get: Callable[[str], StateLike | None], live: Live) -> list[Problem]:
    out = []
    tmax, tmin = model.num(CONF_TEMP_MAX, 30), model.num(CONF_TEMP_MIN, 12)
    for entity in live.temperatures:
        if entity == live.outdoor:
            continue
        st = get(entity)
        t = _num(st)
        if t is None or model.is_outdoor(f"{entity} {_name(st, entity)}"):
            continue  # outdoor thermometers do not have a comfort range
        if t > tmax:
            out.append(
                Problem(
                    f"temp_alta_{entity}",
                    "aviso",
                    "Temperaturas",
                    f"Calor en {_name(st, entity)}",
                    f"{_fmt(t)} °C (máximo {_fmt(tmax, 0)} °C).",
                    entity,
                    1800,
                )
            )
        elif t < tmin:
            out.append(
                Problem(
                    f"temp_baja_{entity}",
                    "aviso",
                    "Temperaturas",
                    f"Frío en {_name(st, entity)}",
                    f"{_fmt(t)} °C (mínimo {_fmt(tmin, 0)} °C).",
                    entity,
                    1800,
                )
            )
    hmax = model.num(CONF_HUMIDITY_MAX, 75)
    for entity in live.humidities:
        st = get(entity)
        h = _num(st)
        if h is not None and h > hmax:
            out.append(
                Problem(
                    f"humedad_{entity}",
                    "info",
                    "Temperaturas",
                    f"Humedad alta en {_name(st, entity)}",
                    f"{h:.0f} % (máximo {hmax:.0f} %): riesgo de condensación y moho.",
                    entity,
                    7200,
                )
            )
    return out


def _gas(model: Model, get: Callable[[str], StateLike | None]) -> list[Problem]:
    entity = model.get(CONF_GAS_FLOW)
    st = get(entity) if entity else None
    flow = _num(st)
    if not flow or flow <= 0 or st is None:
        return []
    hours = model.num(CONF_GAS_FLOW_HOURS, 6)
    return [
        Problem(
            "gas_continuo",
            "aviso",
            "Gas",
            "Consumo de gas continuo",
            f"El contador lleva más de {hours:.0f} h sin parar ({_fmt(flow, 3)} m³/h ahora). Comprueba que no hay una fuga o un aparato encendido.",
            entity,
            hours * 3600,
        )
    ]


def _house(model: Model, states: Iterable[StateLike], now: datetime, skip: frozenset[str] = frozenset()) -> list[Problem]:
    out = []
    check_batteries = bool(model.get(CONF_CHECK_DEVICE_BATTERIES))
    check_safety = bool(model.get(CONF_CHECK_SAFETY))
    if not (check_batteries or check_safety):
        return out
    own = {b.soc for b in model.batteries}
    threshold = model.num(CONF_DEVICE_BATTERY_MIN, 15)
    for st in states:
        domain = st.entity_id.split(".", 1)[0]
        cls = st.attributes.get("device_class")
        if check_batteries and domain == "sensor" and cls == "battery" and st.entity_id not in own and st.entity_id not in skip:
            level = _num(st)
            if level is not None and level <= threshold:
                out.append(
                    Problem(
                        f"pila_{st.entity_id}",
                        "critico" if level <= 5 else "aviso",
                        "Dispositivos",
                        f"Pila baja: {_name(st, st.entity_id)}",
                        f"{level:.0f} %{' — cámbiala ya' if level <= 5 else ''}.",
                        st.entity_id,
                        3600,
                    )
                )
        if check_safety and domain == "binary_sensor" and cls in SAFETY_CLASSES and st.state == "on":
            out.append(
                Problem(
                    f"seguridad_{st.entity_id}",
                    "critico",
                    "Seguridad",
                    SAFETY_CLASSES[cls],
                    f"{_name(st, st.entity_id)} está activo.",
                    st.entity_id,
                    0,
                )
            )
    return out


# ---------------------------------------------------------------------- debounce


@dataclass
class Debouncer:
    """Only report problems that have lasted their ``delay``."""

    first_seen: dict[str, datetime] = field(default_factory=dict)

    def update(self, problems: list[Problem], now: datetime) -> list[tuple[Problem, datetime]]:
        current = {p.id for p in problems}
        for key in [k for k in self.first_seen if k not in current]:
            del self.first_seen[key]
        active = []
        for p in problems:
            since = self.first_seen.setdefault(p.id, now)
            if (now - since).total_seconds() >= p.delay:
                active.append((p, since))
        return active
