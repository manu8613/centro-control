"""Spanish electricity bill (2.0TD) and bill forecasts (pure Python).

The bill follows the order of a real Spanish invoice:

    potencia P1 + potencia P2 + energía − compensación de excedentes
    + impuesto especial sobre la electricidad
    + alquiler del contador + otros cargos fijos (p. ej. financiación del bono social)
    = base imponible → + IVA = total
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
from typing import Any

from .const import FIXED_HOLIDAYS, SOLAR_SEASON
from .energy import Counters, add_months, period_end, period_start

IEE_MIN_EUR_KWH = 0.001  # 1 €/MWh minimum of the electricity tax


def is_valley_day(day: date) -> bool:
    """Weekends and fixed-date national holidays are valley all day in 2.0TD."""
    return day.weekday() >= 5 or (day.month, day.day) in FIXED_HOLIDAYS


def energy_period(moment: datetime) -> str:
    """2.0TD energy period (mainland, Balearic and Canary schedules): P1, P2 or P3."""
    if is_valley_day(moment.date()):
        return "P3"
    hour = moment.hour
    if hour < 8:
        return "P3"
    if 10 <= hour < 14 or 18 <= hour < 22:
        return "P1"
    return "P2"


def power_period(moment: datetime) -> str:
    """2.0TD power period: P1 (08-24 working days) or P2."""
    if is_valley_day(moment.date()) or moment.hour < 8:
        return "P2"
    return "P1"


@dataclass(frozen=True)
class Tariff:
    """Prices and taxes of the electricity contract."""

    mode: str = "periodos"  # sensor | periodos | unico
    p1: float = 0.20
    p2: float = 0.13
    p3: float = 0.09
    flat: float = 0.14
    export_mode: str = "precio_fijo"  # ninguna | precio_fijo | sensor
    export_price: float = 0.05
    export_cap: bool = True
    power_p1_day: float = 0.075902
    power_p2_day: float = 0.001987
    kw_p1: float = 4.6
    kw_p2: float = 4.6
    tax_pct: float = 5.11269632
    vat_pct: float = 21.0
    rental_day: float = 0.02663
    other_day: float = 0.024688

    def energy_price(self, moment: datetime, sensor_price: float | None) -> float | None:
        if self.mode == "sensor":
            return sensor_price
        if self.mode == "unico":
            return self.flat
        return {"P1": self.p1, "P2": self.p2, "P3": self.p3}[energy_period(moment)]

    def export_price_now(self, sensor_price: float | None) -> float:
        if self.export_mode == "ninguna":
            return 0.0
        if self.export_mode == "sensor":
            return max(sensor_price or 0.0, 0.0)
        return self.export_price

    def typical_price(self) -> float:
        """Average energy price used when there is no history yet."""
        if self.mode == "unico":
            return self.flat
        if self.mode == "periodos":
            # 2.0TD hours per week: P1 40 h, P2 40 h, P3 88 h.
            return (self.p1 * 40 + self.p2 * 40 + self.p3 * 88) / 168
        return 0.15


def money(value: float) -> float:
    return round(value + 0.0, 2)


@dataclass
class Bill:
    """An electricity bill (real so far, forecast or simulated)."""

    start: date
    end: date  # exclusive
    days: int
    import_kwh: float
    export_kwh: float
    energy_eur: float
    compensation_eur: float
    power_p1_eur: float
    power_p2_eur: float
    tax_eur: float
    rental_eur: float
    other_eur: float
    base_eur: float
    vat_eur: float
    total_eur: float
    kw_p1: float
    kw_p2: float
    tax_pct: float
    vat_pct: float
    compensation_lost_eur: float = 0.0

    @property
    def avg_price(self) -> float:
        return self.energy_eur / self.import_kwh if self.import_kwh else 0.0

    def lines(self, tariff: Tariff) -> list[dict[str, Any]]:
        out = [
            {
                "concepto": "Potencia punta (P1)",
                "calculo": f"{self.kw_p1:g} kW × {self.days} d × {tariff.power_p1_day:.6f} €/kW·d",
                "importe": money(self.power_p1_eur),
            },
            {
                "concepto": "Potencia valle (P2)",
                "calculo": f"{self.kw_p2:g} kW × {self.days} d × {tariff.power_p2_day:.6f} €/kW·d",
                "importe": money(self.power_p2_eur),
            },
            {
                "concepto": "Energía consumida",
                "calculo": f"{self.import_kwh:.1f} kWh × {self.avg_price:.4f} €/kWh",
                "importe": money(self.energy_eur),
            },
        ]
        if self.compensation_eur or self.export_kwh:
            out.append(
                {
                    "concepto": "Compensación de excedentes",
                    "calculo": f"{self.export_kwh:.1f} kWh vertidos",
                    "importe": money(-self.compensation_eur),
                }
            )
        out += [
            {
                "concepto": "Impuesto sobre la electricidad",
                "calculo": f"{self.tax_pct:.8g} %",
                "importe": money(self.tax_eur),
            },
            {
                "concepto": "Alquiler del contador",
                "calculo": f"{self.days} d × {tariff.rental_day:.6f} €/d",
                "importe": money(self.rental_eur),
            },
        ]
        if self.other_eur:
            out.append(
                {
                    "concepto": "Otros cargos fijos",
                    "calculo": f"{self.days} d × {tariff.other_day:.6f} €/d",
                    "importe": money(self.other_eur),
                }
            )
        return out

    def as_dict(self, tariff: Tariff) -> dict[str, Any]:
        return {
            "desde": self.start.isoformat(),
            "hasta": (self.end - timedelta(days=1)).isoformat(),
            "dias": self.days,
            "importada_kwh": round(self.import_kwh, 2),
            "exportada_kwh": round(self.export_kwh, 2),
            "precio_medio": round(self.avg_price, 5),
            "energia": money(self.energy_eur),
            "compensacion": money(self.compensation_eur),
            "compensacion_perdida": money(self.compensation_lost_eur),
            "potencia": money(self.power_p1_eur + self.power_p2_eur),
            "impuesto_electrico": money(self.tax_eur),
            "alquiler": money(self.rental_eur),
            "otros": money(self.other_eur),
            "base_imponible": money(self.base_eur),
            "iva": money(self.vat_eur),
            "iva_porcentaje": self.vat_pct,
            "total": money(self.total_eur),
            "lineas": self.lines(tariff),
        }


def compute_bill(
    tariff: Tariff,
    start: date,
    end: date,
    days: int,
    import_kwh: float,
    export_kwh: float,
    energy_eur: float,
    compensation_eur: float,
) -> Bill:
    """Bill for ``days`` days of a period with the given energy totals."""
    power_p1 = tariff.kw_p1 * days * tariff.power_p1_day
    power_p2 = tariff.kw_p2 * days * tariff.power_p2_day
    lost = 0.0
    if tariff.export_cap and compensation_eur > energy_eur:
        lost = compensation_eur - energy_eur
        compensation_eur = energy_eur
    taxable = power_p1 + power_p2 + energy_eur - compensation_eur
    tax = max(taxable * tariff.tax_pct / 100.0, import_kwh * IEE_MIN_EUR_KWH) if taxable > 0 else 0.0
    rental = days * tariff.rental_day
    other = days * tariff.other_day
    base = taxable + tax + rental + other
    vat = base * tariff.vat_pct / 100.0
    return Bill(
        start=start,
        end=end,
        days=days,
        import_kwh=import_kwh,
        export_kwh=export_kwh,
        energy_eur=energy_eur,
        compensation_eur=compensation_eur,
        power_p1_eur=power_p1,
        power_p2_eur=power_p2,
        tax_eur=tax,
        rental_eur=rental,
        other_eur=other,
        base_eur=base,
        vat_eur=vat,
        total_eur=base + vat,
        kw_p1=tariff.kw_p1,
        kw_p2=tariff.kw_p2,
        tax_pct=tariff.tax_pct,
        vat_pct=tariff.vat_pct,
        compensation_lost_eur=lost,
    )


# ====================================================================== forecasts


@dataclass(frozen=True)
class Scenario:
    """What-if changes for the simulator (all neutral by default)."""

    consumption_pct: float = 0.0
    price_pct: float = 0.0
    extra_wp: float = 0.0
    kw_p1: float | None = None
    kw_p2: float | None = None
    export_price: float | None = None
    extra_battery_kwh: float = 0.0


@dataclass
class Daily:
    """Average day used by the forecasts."""

    solar: float
    load: float
    imported: float
    exported: float
    price: float
    export_price: float
    month: int
    source: str
    days: int


def _avg(totals: dict[str, float], key: str, days: int) -> float:
    return totals.get(key, 0.0) / days if days else 0.0


def recent_day(counters: Counters, tariff: Tariff, today: date, window: int = 30) -> Daily:
    """Average day of the last ``window`` complete days (or the current period)."""
    found, totals = counters.window(today, window)
    source = "ultimos_dias"
    if found < 3:
        found = max((today - period_start(today, counters.billing_day)).days, 0)
        totals = {m: counters.get(m, "factura") - counters.get(m, "hoy") for m in counters.values}
        source = "factura_en_curso"
        if found < 1:
            found = 1
            totals = {m: counters.get(m, "hoy") for m in counters.values}
            source = "hoy"
    imported = _avg(totals, "importada", found)
    exported = _avg(totals, "exportada", found)
    cost = totals.get("coste_energia", 0.0)
    comp = totals.get("compensacion", 0.0)
    price = cost / totals["importada"] if totals.get("importada") else tariff.typical_price()
    export_price = comp / totals["exportada"] if totals.get("exportada") else tariff.export_price_now(None)
    center = today - timedelta(days=max(found // 2, 1))
    return Daily(
        solar=_avg(totals, "solar", found),
        load=_avg(totals, "consumo", found),
        imported=imported,
        exported=exported,
        price=price or tariff.typical_price(),
        export_price=export_price,
        month=center.month,
        source=source,
        days=found,
    )


def project_day(base: Daily, month: int, peak_wp: float, scenario: Scenario) -> Daily:
    """Move an average day to another month (solar seasonality) and apply a scenario."""
    season = SOLAR_SEASON[month - 1] / SOLAR_SEASON[base.month - 1]
    solar = base.solar * season
    if scenario.extra_wp and peak_wp > 0:
        solar *= (peak_wp + scenario.extra_wp) / peak_wp
    load = (base.load or base.imported + max(base.solar - base.exported, 0.0)) * (1 + scenario.consumption_pct / 100)
    used = max(base.solar - base.exported, 0.0)
    ratio = used / base.solar if base.solar > 0 else 1.0
    if scenario.extra_battery_kwh > 0:
        ratio = min(1.0, ratio + scenario.extra_battery_kwh / max(base.solar, 1e-6))
    self_used = min(load, solar * ratio)
    return Daily(
        solar=solar,
        load=load,
        imported=max(load - self_used, 0.0),
        exported=max(solar - self_used, 0.0),
        price=base.price * (1 + scenario.price_pct / 100),
        export_price=base.export_price if scenario.export_price is None else scenario.export_price,
        month=month,
        source=base.source,
        days=base.days,
    )


def _scenario_tariff(tariff: Tariff, scenario: Scenario) -> Tariff:
    return replace(
        tariff,
        kw_p1=tariff.kw_p1 if scenario.kw_p1 is None else scenario.kw_p1,
        kw_p2=tariff.kw_p2 if scenario.kw_p2 is None else scenario.kw_p2,
    )


def bill_from_day(tariff: Tariff, start: date, end: date, day: Daily) -> Bill:
    days = (end - start).days
    return compute_bill(
        tariff,
        start,
        end,
        days,
        import_kwh=day.imported * days,
        export_kwh=day.exported * days,
        energy_eur=day.imported * days * day.price,
        compensation_eur=day.exported * days * day.export_price,
    )


def current_bill(counters: Counters, tariff: Tariff, today: date) -> Bill:
    """Bill of the running period up to today (today included)."""
    start = period_start(today, counters.billing_day)
    days = (today - start).days + 1
    return compute_bill(
        tariff,
        start,
        period_end(start),
        days,
        import_kwh=counters.get("importada", "factura"),
        export_kwh=counters.get("exportada", "factura"),
        energy_eur=counters.get("coste_energia", "factura"),
        compensation_eur=counters.get("compensacion", "factura"),
    )


def forecast_current(counters: Counters, tariff: Tariff, today: date, now_fraction: float) -> Bill:
    """End-of-period forecast: what is already spent plus the average for the rest."""
    start = period_start(today, counters.billing_day)
    end = period_end(start)
    total_days = (end - start).days
    elapsed = (today - start).days + now_fraction
    base = recent_day(counters, tariff, today)
    remaining = max(total_days - elapsed, 0.0)
    imported = counters.get("importada", "factura") + base.imported * remaining
    exported = counters.get("exportada", "factura") + base.exported * remaining
    energy = counters.get("coste_energia", "factura") + base.imported * remaining * base.price
    comp = counters.get("compensacion", "factura") + base.exported * remaining * base.export_price
    return compute_bill(tariff, start, end, total_days, imported, exported, energy, comp)


def forecast_next(
    counters: Counters,
    tariff: Tariff,
    today: date,
    peak_wp: float,
    count: int = 3,
    scenario: Scenario | None = None,
) -> list[dict[str, Any]]:
    """Forecast of the next ``count`` bills after the running one."""
    scenario = scenario or Scenario()
    sim_tariff = _scenario_tariff(tariff, scenario)
    base = recent_day(counters, tariff, today)
    start = period_end(period_start(today, counters.billing_day))
    out = []
    for _ in range(count):
        end = period_end(start)
        mid = start + (end - start) / 2
        day = project_day(base, mid.month, peak_wp, scenario)
        source = "modelo"
        # Same period last year, if we have it, beats the model.
        found, totals = counters.range_totals(add_months(start, -12), add_months(end, -12))
        if found >= 0.8 * (end - start).days:
            day = Daily(
                solar=_avg(totals, "solar", found),
                load=_avg(totals, "consumo", found) * (1 + scenario.consumption_pct / 100),
                imported=_avg(totals, "importada", found) * (1 + scenario.consumption_pct / 100),
                exported=_avg(totals, "exportada", found),
                price=day.price,
                export_price=day.export_price,
                month=mid.month,
                source="historico",
                days=found,
            )
            source = "año_anterior"
        bill = bill_from_day(sim_tariff, start, end, day)
        item = bill.as_dict(sim_tariff)
        item.update(
            {
                "mes": mid.strftime("%Y-%m"),
                "fuente": source,
                "solar_kwh": round(day.solar * bill.days, 1),
                "consumo_kwh": round(day.load * bill.days, 1),
            }
        )
        out.append(item)
        start = end
    return out


def simulate(
    counters: Counters,
    tariff: Tariff,
    today: date,
    peak_wp: float,
    scenario: Scenario,
) -> dict[str, Any]:
    """Next bill with and without the scenario, to show the difference."""
    base = forecast_next(counters, tariff, today, peak_wp, 1)[0]
    sim = forecast_next(counters, tariff, today, peak_wp, 1, scenario)[0]
    return {
        "base": base,
        "simulada": sim,
        "diferencia": money(sim["total"] - base["total"]),
        "diferencia_anual": money((sim["total"] - base["total"]) * 12),
    }
