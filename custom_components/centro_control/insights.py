"""Derived figures: self-sufficiency, solar savings and CO2 (pure Python)."""

from __future__ import annotations

from typing import Any

from .energy import BUCKETS, Counters

ALL_BUCKETS = (*BUCKETS, "ayer")


def ratios(counters: Counters, bucket: str) -> dict[str, float]:
    """Autoconsumo and autosuficiencia (%) for one bucket."""
    solar = counters.get("solar", bucket)
    exported = counters.get("exportada", bucket)
    imported = counters.get("importada", bucket)
    load = counters.get("consumo", bucket)
    used = max(solar - exported, 0.0)
    if not load:
        load = imported + used
    return {
        "autoconsumida_kwh": round(used, 3),
        "autoconsumo_pct": round(100 * used / solar, 1) if solar else 0.0,
        "autosuficiencia_pct": round(100 * max(1 - imported / load, 0.0), 1) if load else 0.0,
    }


def savings(counters: Counters, bucket: str, fallback_price: float) -> float:
    """€ saved by the solar system: self-used kWh at the average price + compensation."""
    imported = counters.get("importada", bucket)
    cost = counters.get("coste_energia", bucket)
    price = cost / imported if imported > 0.05 else fallback_price
    used = max(counters.get("solar", bucket) - counters.get("exportada", bucket), 0.0)
    return round(used * price + counters.get("compensacion", bucket), 2)


def co2(counters: Counters, bucket: str, tree_kg_year: float, car_kg_km: float) -> dict[str, Any]:
    avoided = counters.get("co2_evitado", bucket)
    grid = counters.get("co2_red", bucket)
    gas = counters.get("co2_gas", bucket)
    return {
        "evitado_kg": round(avoided, 2),
        "red_kg": round(grid, 2),
        "gas_kg": round(gas, 2),
        "neto_kg": round(grid + gas - avoided, 2),
        "arboles": round(avoided / tree_kg_year, 2) if tree_kg_year else 0.0,
        "km_coche": round(avoided / car_kg_km, 1) if car_kg_km else 0.0,
    }


def summary(counters: Counters, fallback_price: float, tree: float, car: float) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for bucket in ALL_BUCKETS:
        out[bucket] = {
            **ratios(counters, bucket),
            "ahorro_eur": savings(counters, bucket, fallback_price),
            **{f"co2_{k}": v for k, v in co2(counters, bucket, tree, car).items()},
        }
    return out
