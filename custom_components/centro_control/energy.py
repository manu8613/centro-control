"""Energy bookkeeping (pure Python, no Home Assistant).

* ``Counters`` keeps every metric per period (hoy, mes, factura, año, total)
  and a daily history, and rolls the periods over at midnight.
* ``Meter`` turns readings of an energy meter into safe increments.
* ``Integrator`` turns power samples into energy (trapezoids).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

BUCKETS = ("hoy", "mes", "factura", "ano", "total")

POWER_UNITS = {"W": 1.0, "kW": 1000.0, "MW": 1_000_000.0, "mW": 0.001}
ENERGY_UNITS = {"Wh": 0.001, "kWh": 1.0, "MWh": 1000.0, "GWh": 1_000_000.0}


def to_watts(value: float, unit: str | None) -> float:
    return value * POWER_UNITS.get(unit or "W", 1.0)


def to_kwh(value: float, unit: str | None) -> float:
    return value * ENERGY_UNITS.get(unit or "kWh", 1.0)


def period_start(day: date, billing_day: int) -> date:
    """First day of the billing period that contains ``day``."""
    billing_day = max(1, min(28, int(billing_day)))
    if day.day >= billing_day:
        return day.replace(day=billing_day)
    month = day.month - 1 or 12
    year = day.year - (1 if day.month == 1 else 0)
    return date(year, month, billing_day)


def add_months(day: date, months: int) -> date:
    month = day.month - 1 + months
    year = day.year + month // 12
    return date(year, month % 12 + 1, min(day.day, 28))


def period_end(start: date) -> date:
    """Exclusive end of the billing period starting on ``start``."""
    return add_months(start, 1)


@dataclass
class Counters:
    """Metric totals per bucket plus a daily history."""

    billing_day: int = 1
    values: dict[str, dict[str, float]] = field(default_factory=dict)
    keys: dict[str, str] = field(default_factory=dict)
    history: dict[str, dict[str, float]] = field(default_factory=dict)
    history_days: int = 800

    # ---------------------------------------------------------------- keys
    def _keys_for(self, day: date) -> dict[str, str]:
        return {
            "hoy": day.isoformat(),
            "mes": day.strftime("%Y-%m"),
            "factura": period_start(day, self.billing_day).isoformat(),
            "ano": str(day.year),
            "total": "total",
        }

    def roll(self, day: date) -> bool:
        """Close the buckets whose period ended. Returns True if a day closed."""
        new = self._keys_for(day)
        if not self.keys:
            self.keys = new
            return False
        closed = False
        if self.keys.get("hoy") != new["hoy"]:
            old_day = self.keys.get("hoy")
            if old_day:
                record = self.history.setdefault(old_day, {})
                for metric, buckets in self.values.items():
                    value = buckets.get("hoy", 0.0)
                    if value:
                        record[metric] = round(record.get(metric, 0.0) + value, 6)
            closed = True
        for bucket in BUCKETS:
            if self.keys.get(bucket) != new[bucket]:
                for buckets in self.values.values():
                    buckets[bucket] = 0.0
        self.keys = new
        if closed:
            self._prune(day)
        return closed

    def _prune(self, day: date) -> None:
        oldest = (day - timedelta(days=self.history_days)).isoformat()
        for key in [k for k in self.history if k < oldest]:
            del self.history[key]

    # ---------------------------------------------------------------- values
    def add(self, metric: str, value: float, day: date) -> None:
        if not value:
            return
        self.roll(day)
        buckets = self.values.setdefault(metric, dict.fromkeys(BUCKETS, 0.0))
        for bucket in BUCKETS:
            buckets[bucket] = buckets.get(bucket, 0.0) + value

    def get(self, metric: str, bucket: str = "hoy") -> float:
        if bucket == "ayer":
            yesterday = self.keys.get("hoy")
            if not yesterday:
                return 0.0
            key = (date.fromisoformat(yesterday) - timedelta(days=1)).isoformat()
            return self.history.get(key, {}).get(metric, 0.0)
        return self.values.get(metric, {}).get(bucket, 0.0)

    def buckets(self, metric: str) -> dict[str, float]:
        out = {b: round(self.get(metric, b), 4) for b in BUCKETS}
        out["ayer"] = round(self.get(metric, "ayer"), 4)
        return out

    def set_billing_day(self, billing_day: int, day: date) -> None:
        """Changing the billing day starts a new 'factura' bucket from the history."""
        billing_day = max(1, min(28, int(billing_day)))
        if billing_day == self.billing_day:
            return
        self.billing_day = billing_day
        start = period_start(day, billing_day)
        totals: dict[str, float] = {}
        current = start
        while current < day:
            for metric, value in self.history.get(current.isoformat(), {}).items():
                totals[metric] = totals.get(metric, 0.0) + value
            current += timedelta(days=1)
        for metric, buckets in self.values.items():
            buckets["factura"] = totals.get(metric, 0.0) + buckets.get("hoy", 0.0)
        self.keys["factura"] = start.isoformat()

    def import_days(self, records: dict[str, dict[str, float]], today: date) -> int:
        """Add past days (e.g. from the recorder) that are not in the history yet.

        The days also count towards the month, billing period, year and total
        buckets they belong to. Returns how many days were added.
        """
        self.roll(today)
        start = period_start(today, self.billing_day)
        added = 0
        for key in sorted(records):
            day = date.fromisoformat(key)
            if day >= today or key in self.history or not records[key]:
                continue
            self.history[key] = {m: round(v, 6) for m, v in records[key].items() if v}
            added += 1
            for metric, value in self.history[key].items():
                buckets = self.values.setdefault(metric, dict.fromkeys(BUCKETS, 0.0))
                buckets["total"] = buckets.get("total", 0.0) + value
                if day.year == today.year:
                    buckets["ano"] = buckets.get("ano", 0.0) + value
                    if day.month == today.month:
                        buckets["mes"] = buckets.get("mes", 0.0) + value
                if day >= start:
                    buckets["factura"] = buckets.get("factura", 0.0) + value
        self._prune(today)
        return added

    # ---------------------------------------------------------------- history
    def days(self, metric: str, last: int, day: date) -> list[tuple[str, float]]:
        """Daily values for the ``last`` days up to ``day`` (today included)."""
        out = []
        for offset in range(last - 1, -1, -1):
            current = day - timedelta(days=offset)
            key = current.isoformat()
            if current == day:
                value = self.get(metric, "hoy")
            else:
                value = self.history.get(key, {}).get(metric, 0.0)
            out.append((key, round(value, 4)))
        return out

    def window(self, day: date, length: int) -> tuple[int, dict[str, float]]:
        """Sum of the complete days before ``day`` (up to ``length``) and how many had data."""
        totals: dict[str, float] = {}
        found = 0
        for offset in range(1, length + 1):
            record = self.history.get((day - timedelta(days=offset)).isoformat())
            if not record:
                continue
            found += 1
            for metric, value in record.items():
                totals[metric] = totals.get(metric, 0.0) + value
        return found, totals

    def range_totals(self, start: date, end: date) -> tuple[int, dict[str, float]]:
        """Sum of history between ``start`` (incl.) and ``end`` (excl.)."""
        totals: dict[str, float] = {}
        found = 0
        current = start
        while current < end:
            record = self.history.get(current.isoformat())
            if record:
                found += 1
                for metric, value in record.items():
                    totals[metric] = totals.get(metric, 0.0) + value
            current += timedelta(days=1)
        return found, totals

    def months(self, metric: str, count: int, day: date) -> list[tuple[str, float]]:
        """Monthly totals for the last ``count`` months (current month included)."""
        totals: dict[str, float] = {}
        for key, record in self.history.items():
            totals[key[:7]] = totals.get(key[:7], 0.0) + record.get(metric, 0.0)
        current = day.strftime("%Y-%m")
        totals[current] = totals.get(current, 0.0) + self.get(metric, "hoy")
        out = []
        first = add_months(day.replace(day=1), -(count - 1))
        for i in range(count):
            key = add_months(first, i).strftime("%Y-%m")
            out.append((key, round(totals.get(key, 0.0), 3)))
        return out

    # ---------------------------------------------------------------- storage
    def as_dict(self) -> dict[str, Any]:
        return {
            "billing_day": self.billing_day,
            "values": self.values,
            "keys": self.keys,
            "history": self.history,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None, billing_day: int, history_days: int = 800) -> Counters:
        data = data or {}
        counters = cls(
            billing_day=int(data.get("billing_day", billing_day)),
            values={m: {b: float(v) for b, v in bk.items()} for m, bk in data.get("values", {}).items()},
            keys=dict(data.get("keys", {})),
            history={d: {m: float(v) for m, v in rec.items()} for d, rec in data.get("history", {}).items()},
            history_days=history_days,
        )
        return counters


@dataclass
class Meter:
    """Increments of a cumulative energy meter, robust to resets and glitches."""

    last: float | None = None
    last_ts: float | None = None
    max_kw: float = 60.0

    def update(self, value: float, ts: float) -> float:
        if self.last is None or self.last_ts is None:
            self.last, self.last_ts = value, ts
            return 0.0
        hours = max((ts - self.last_ts) / 3600.0, 1 / 60)
        delta = value - self.last
        self.last, self.last_ts = value, ts
        if delta <= 0:
            # Decrease: daily reset or glitch. Start again from here.
            return 0.0
        if delta > self.max_kw * hours:
            # Implausible jump (sensor came back from 0, unit change...).
            return 0.0
        return delta

    def as_dict(self) -> dict[str, float | None]:
        return {"last": self.last, "last_ts": self.last_ts}

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None, max_kw: float = 60.0) -> Meter:
        data = data or {}
        return cls(last=data.get("last"), last_ts=data.get("last_ts"), max_kw=max_kw)


@dataclass
class Integrator:
    """Energy (kWh) from power samples (W)."""

    max_gap: float = 120.0
    last_ts: float | None = None
    last_w: float | None = None

    def sample(self, watts: float | None, ts: float) -> float:
        if watts is None:
            self.last_ts = self.last_w = None
            return 0.0
        if self.last_ts is None or self.last_w is None:
            self.last_ts, self.last_w = ts, watts
            return 0.0
        dt = ts - self.last_ts
        previous = self.last_w
        self.last_ts, self.last_w = ts, watts
        if dt <= 0 or dt > self.max_gap:
            return 0.0
        return (previous + watts) / 2.0 * dt / 3_600_000.0
