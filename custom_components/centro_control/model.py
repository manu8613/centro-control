"""Typed view of the user's configuration (pure Python, no Home Assistant).

The config entry keeps the general settings in ``options`` and every string,
battery, circuit and irrigation zone as a config subentry. ``Model`` turns
that into plain dataclasses the rest of the integration can use.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
import re
from typing import Any

from .const import (
    BAT_POSITIVE_CHARGE,
    CONF_ALARMS,
    CONF_BANK,
    CONF_BATTERY_SIGN,
    CONF_CAPACITY,
    CONF_CELL_DIFF,
    CONF_CELL_HIGH,
    CONF_CELL_LOW,
    CONF_CELLS,
    CONF_CLIMATES,
    CONF_CURRENT,
    CONF_CYCLES,
    CONF_ENERGY,
    CONF_GRID_SIGN,
    CONF_GROUP,
    CONF_HUMIDITIES,
    CONF_ICON,
    CONF_IN_TOTAL,
    CONF_LIGHTS,
    CONF_LINK,
    CONF_LIGHTS_EXCLUDE,
    CONF_MAX_MINUTES,
    CONF_MINUTES,
    CONF_NAME,
    CONF_OUTDOOR_PATTERN,
    CONF_PARENT,
    CONF_PEAK,
    CONF_POWER,
    CONF_SOC,
    CONF_SOIL,
    CONF_TEMP_EXCLUDE_PATTERN,
    CONF_TEMPERATURE,
    CONF_TEMPERATURES,
    CONF_VALVE,
    CONF_VOLTAGE,
    DEFAULTS,
    GRID_POSITIVE_EXPORT,
    SUB_BATTERY,
    SUB_CIRCUIT,
    SUB_STRING,
    SUB_ZONE,
)


def slug(text: str) -> str:
    """Lower-case ascii slug used in unique ids and metric names."""
    table = str.maketrans("áéíóúüñÁÉÍÓÚÜÑ", "aeiouunAEIOUUN")
    value = re.sub(r"[^a-z0-9]+", "_", text.translate(table).lower()).strip("_")
    return value or "x"


def _list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    return [v for v in value if v]


@dataclass(frozen=True)
class PVString:
    id: str
    name: str
    power: str
    voltage: str | None = None
    current: str | None = None
    energy: str | None = None
    peak_wp: float = 0.0
    group: str = "A"

    @property
    def metric(self) -> str:
        return f"string_{self.id}"


@dataclass(frozen=True)
class Battery:
    id: str
    name: str
    soc: str
    power: str
    positive_charge: bool = False
    voltage: str | None = None
    current: str | None = None
    temperatures: tuple[str, ...] = ()
    capacity_kwh: float = 0.0
    cells: tuple[str, ...] = ()
    cell_low: str | None = None
    cell_high: str | None = None
    cell_diff: str | None = None
    alarms: str | None = None
    cycles: str | None = None
    link: str | None = None
    in_total: bool = True


@dataclass(frozen=True)
class Circuit:
    id: str
    name: str
    power: str
    energy: str | None = None
    group: str = "Cuadro"
    parent: str | None = None
    in_total: bool = True
    icon: str = "mdi:flash"

    @property
    def metric(self) -> str:
        return f"circuito_{self.id}"


@dataclass(frozen=True)
class Zone:
    id: str
    name: str
    valve: str
    soil: str | None = None
    minutes: float = 10.0
    max_minutes: float = 60.0


@dataclass
class Model:
    """Everything the user configured."""

    settings: dict[str, Any]
    strings: list[PVString] = field(default_factory=list)
    batteries: list[Battery] = field(default_factory=list)
    circuits: list[Circuit] = field(default_factory=list)
    zones: list[Zone] = field(default_factory=list)

    # ------------------------------------------------------------ building
    @classmethod
    def build(
        cls,
        data: Mapping[str, Any],
        options: Mapping[str, Any],
        subentries: Iterable[tuple[str, str, Mapping[str, Any]]],
    ) -> Model:
        """``subentries`` yields ``(subentry_id, subentry_type, data)``."""
        settings = {**DEFAULTS, **data, **options}
        model = cls(settings=settings)
        for sub_id, kind, sub in subentries:
            name = str(sub.get(CONF_NAME) or kind)
            if kind == SUB_STRING:
                model.strings.append(
                    PVString(
                        id=sub_id,
                        name=name,
                        power=sub.get(CONF_POWER) or "",
                        voltage=sub.get(CONF_VOLTAGE) or None,
                        current=sub.get(CONF_CURRENT) or None,
                        energy=sub.get(CONF_ENERGY) or None,
                        peak_wp=float(sub.get(CONF_PEAK) or 0),
                        group=str(sub.get(CONF_GROUP) or "A"),
                    )
                )
            elif kind == SUB_BATTERY:
                model.batteries.append(
                    Battery(
                        id=sub_id,
                        name=name,
                        soc=sub.get(CONF_SOC) or "",
                        power=sub.get(CONF_POWER) or "",
                        positive_charge=sub.get(CONF_BATTERY_SIGN) == BAT_POSITIVE_CHARGE,
                        voltage=sub.get(CONF_VOLTAGE) or None,
                        current=sub.get(CONF_CURRENT) or None,
                        temperatures=tuple(_list(sub.get(CONF_TEMPERATURE))),
                        capacity_kwh=float(sub.get(CONF_CAPACITY) or 0),
                        cells=tuple(_list(sub.get(CONF_CELLS))),
                        cell_low=sub.get(CONF_CELL_LOW) or None,
                        cell_high=sub.get(CONF_CELL_HIGH) or None,
                        cell_diff=sub.get(CONF_CELL_DIFF) or None,
                        alarms=sub.get(CONF_ALARMS) or None,
                        cycles=sub.get(CONF_CYCLES) or None,
                        link=sub.get(CONF_LINK) or None,
                        in_total=bool(sub.get(CONF_BANK, True)),
                    )
                )
            elif kind == SUB_CIRCUIT:
                model.circuits.append(
                    Circuit(
                        id=sub_id,
                        name=name,
                        power=sub.get(CONF_POWER) or "",
                        energy=sub.get(CONF_ENERGY) or None,
                        group=str(sub.get(CONF_GROUP) or "Cuadro"),
                        parent=sub.get(CONF_PARENT) or None,
                        in_total=bool(sub.get(CONF_IN_TOTAL, True)),
                        icon=str(sub.get(CONF_ICON) or "mdi:flash"),
                    )
                )
            elif kind == SUB_ZONE:
                model.zones.append(
                    Zone(
                        id=sub_id,
                        name=name,
                        valve=sub.get(CONF_VALVE) or "",
                        soil=sub.get(CONF_SOIL) or None,
                        minutes=float(sub.get(CONF_MINUTES) or 10),
                        max_minutes=float(sub.get(CONF_MAX_MINUTES) or 60),
                    )
                )
        model.strings.sort(key=lambda s: s.name)
        model.batteries.sort(key=lambda b: (not b.in_total, b.name))
        model.circuits.sort(key=lambda c: (c.group, c.name))
        model.zones.sort(key=lambda z: z.name)
        return model

    # ------------------------------------------------------------ helpers
    def get(self, key: str, default: Any = None) -> Any:
        value = self.settings.get(key, default)
        return default if value in (None, "") else value

    def num(self, key: str, default: float = 0.0) -> float:
        try:
            return float(self.get(key, default))
        except (TypeError, ValueError):
            return default

    @property
    def grid_inverted(self) -> bool:
        return self.get(CONF_GRID_SIGN) == GRID_POSITIVE_EXPORT

    @property
    def bank(self) -> list[Battery]:
        """Batteries that count for the totals (SOC, power, energy)."""
        return [b for b in self.batteries if b.in_total]

    @property
    def soc_pair(self) -> list[Battery]:
        """Batteries whose SOCs are compared: the detail-only ones (e.g. each
        BMS behind an inverter that already gives the bank SOC) or, if there
        are fewer than two of those, every battery."""
        detail = [b for b in self.batteries if not b.in_total]
        if len(detail) >= 2:
            return detail
        return list(self.batteries) if len(self.batteries) >= 2 else []

    @property
    def capacity_kwh(self) -> float:
        return sum(b.capacity_kwh for b in self.bank)

    @property
    def peak_wp(self) -> float:
        from .const import CONF_PV_PEAK

        configured = self.num(CONF_PV_PEAK)
        return configured or sum(s.peak_wp for s in self.strings)

    def lights(self) -> list[str]:
        return _list(self.get(CONF_LIGHTS))

    def lights_excluded(self) -> set[str]:
        return set(_list(self.get(CONF_LIGHTS_EXCLUDE)))

    def temperatures(self) -> list[str]:
        return _list(self.get(CONF_TEMPERATURES))

    def humidities(self) -> list[str]:
        return _list(self.get(CONF_HUMIDITIES))

    def climates(self) -> list[str]:
        return _list(self.get(CONF_CLIMATES))

    def is_outdoor(self, name: str) -> bool:
        pattern = self.get(CONF_OUTDOOR_PATTERN)
        try:
            return bool(pattern and re.search(pattern, name, re.IGNORECASE))
        except re.error:
            return False

    def temp_excluded(self, text: str) -> bool:
        pattern = self.get(CONF_TEMP_EXCLUDE_PATTERN)
        try:
            return bool(pattern and re.search(pattern, text, re.IGNORECASE))
        except re.error:
            return False

    def energy_entities(self) -> set[str]:
        """Every source entity used by the energy part (to keep them out of lists)."""
        found: set[str] = set()
        for value in self.settings.values():
            if (
                isinstance(value, str)
                and value.count(".") == 1
                and value.split(".")[0]
                in (
                    "sensor",
                    "binary_sensor",
                )
            ):
                found.add(value)
        for s in self.strings:
            found.update(e for e in (s.power, s.voltage, s.current, s.energy) if e)
        for b in self.batteries:
            found.update(e for e in (b.soc, b.power, b.voltage, b.current, b.cell_low, b.cell_high, b.cell_diff, b.alarms, b.cycles, b.link) if e)
            found.update(b.temperatures)
            found.update(b.cells)
        for c in self.circuits:
            found.update(e for e in (c.power, c.energy) if e)
        return found

    def sources(self) -> list[tuple[str, str, str]]:
        """``(area, label, entity_id)`` of every configured source, for availability checks."""
        from .const import (
            CONF_GAS_METER,
            CONF_GRID_POWER,
            CONF_INV_TEMP,
            CONF_LOAD_POWER,
            CONF_PRICE_MODE,
            CONF_PRICE_SENSOR,
            CONF_PV_POWER,
            PRICE_SENSOR,
        )

        out: list[tuple[str, str, str]] = []

        def add(area: str, label: str, entity: str | None) -> None:
            if entity:
                out.append((area, label, entity))

        add("Red", "Potencia de red", self.get(CONF_GRID_POWER))
        add("Consumo", "Consumo total", self.get(CONF_LOAD_POWER))
        add("Solar", "Potencia solar", self.get(CONF_PV_POWER))
        add("Solar", "Temperatura del inversor", self.get(CONF_INV_TEMP))
        if self.get(CONF_PRICE_MODE) == PRICE_SENSOR:
            add("Coste", "Precio de la luz", self.get(CONF_PRICE_SENSOR))
        add("Gas", "Lectura de gas", self.get(CONF_GAS_METER))
        for s in self.strings:
            add("Solar", s.name, s.power)
        for b in self.batteries:
            add("Batería", f"{b.name} · SOC", b.soc)
            add("Batería", f"{b.name} · potencia", b.power)
        for c in self.circuits:
            add("Consumo", c.name, c.power)
        for z in self.zones:
            add("Riego", z.name, z.valve)
        return out


def circuit_children(model: Model) -> dict[str | None, list[Circuit]]:
    """Circuits grouped by the name of their parent (``None`` = top level)."""
    names = {c.name for c in model.circuits}
    tree: dict[str | None, list[Circuit]] = {}
    for c in model.circuits:
        parent = c.parent if c.parent in names and c.parent != c.name else None
        tree.setdefault(parent, []).append(c)
    return tree


__all__ = [
    "Battery",
    "Circuit",
    "Model",
    "PVString",
    "Zone",
    "circuit_children",
    "slug",
]
