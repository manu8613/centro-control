"""Create the Centro de Control dashboard in the sidebar.

The dashboard is a YAML-mode Lovelace dashboard generated from the real entity
ids, so it always matches the installed entities. It is rebuilt on every load
(and with the "Regenerar panel" button), and the YAML is kept in
``config/centro_control/`` so it can be copied into another dashboard.
"""

from __future__ import annotations

from dataclasses import asdict
import logging
from pathlib import Path
from typing import Any

from homeassistant.components import frontend, persistent_notification
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.util.yaml import dump

from .const import (
    AUTHOR,
    AUTHOR_URL,
    DASHBOARD_ICON,
    DASHBOARD_URL,
    DOMAIN,
    REPO_URL,
    SUB_CIRCUIT,
    SUB_STRING,
    SUB_ZONE,
    VERSION,
)
from .manager import CentroConfigEntry, CentroManager
from .panel import Light, PanelContext, build_panel
from .sensor import MAIN

_LOGGER = logging.getLogger(__name__)

_OURS = f"{DOMAIN}_panels"

MAIN_KEYS: dict[str, str] = {
    **{d.key: "sensor" for d in MAIN},
    "problema_critico": "binary_sensor",
    "riego_activo": "binary_sensor",
    "periodo": "select",
    "omitir_si_llueve": "switch",
    "reconocer_problemas": "button",
    "apagar_luces": "button",
    "regenerar_panel": "button",
    "importar_historico": "button",
    "parar_riego": "button",
    "sim_potencia_p1": "number",
    "sim_potencia_p2": "number",
    "sim_consumo": "number",
    "sim_precio": "number",
    "sim_paneles": "number",
    "sim_bateria": "number",
    "sim_excedentes": "number",
}
SUB_KEYS: dict[str, dict[str, str]] = {
    SUB_STRING: {"energia_string": "sensor"},
    SUB_CIRCUIT: {"energia_circuito": "sensor"},
    SUB_ZONE: {"riego_restante": "sensor", "regar": "button", "minutos_riego": "number"},
}


def panel_path(hass: HomeAssistant, entry_id: str) -> Path:
    return Path(hass.config.path(DOMAIN, f"panel_{entry_id}.yaml"))


def remove_panel_file(hass: HomeAssistant, entry_id: str) -> None:
    path = panel_path(hass, entry_id)
    if path.exists():
        path.unlink()


def dashboard_url(hass: HomeAssistant, entry: CentroConfigEntry) -> str:
    entries = sorted(hass.config_entries.async_entries(DOMAIN), key=lambda e: e.entry_id)
    index = next((i for i, e in enumerate(entries) if e.entry_id == entry.entry_id), 0)
    return DASHBOARD_URL if index == 0 else f"{DASHBOARD_URL}-{index + 1}"


def entity_ids(hass: HomeAssistant, entry: CentroConfigEntry) -> dict[str, str]:
    registry = er.async_get(hass)
    ids: dict[str, str] = {}
    for key, platform in MAIN_KEYS.items():
        found = registry.async_get_entity_id(platform, DOMAIN, f"{entry.entry_id}_{key}")
        ids[key] = found or f"{platform}.{DOMAIN}_{key}"
    for sub_id, sub in entry.subentries.items():
        for key, platform in SUB_KEYS.get(sub.subentry_type, {}).items():
            found = registry.async_get_entity_id(platform, DOMAIN, f"{entry.entry_id}_{sub_id}_{key}")
            ids[f"{sub_id}:{key}"] = found or f"{platform}.{DOMAIN}_{sub_id.lower()}_{key}"
    return ids


def build_context(hass: HomeAssistant, manager: CentroManager) -> PanelContext:
    entry = manager.config_entry
    m = manager.model
    lights = []
    for e in manager.light_entities():
        st = hass.states.get(e)
        name = str(st.attributes.get("friendly_name", e)) if st else e
        modes = (st.attributes.get("supported_color_modes") or []) if st else []
        dimmable = any(mode != "onoff" for mode in modes)
        lights.append(Light(e, name, m.is_outdoor(f"{e} {name}"), dimmable))
    lights.sort(key=lambda li: li.name.lower())
    return PanelContext(
        title=entry.title,
        ids=entity_ids(hass, entry),
        settings=dict(m.settings),
        strings=[
            {"id": s.id, "name": s.name, "power": s.power, "voltage": s.voltage, "current": s.current, "peak_wp": s.peak_wp}
            for s in m.strings
        ],
        batteries=[
            {
                "id": b.id,
                "name": b.name,
                "soc": b.soc,
                "power": b.power,
                "voltage": b.voltage,
                "current": b.current,
                "temperatures": list(b.temperatures),
                "cells": list(b.cells),
                "cycles": b.cycles,
                "positive_charge": b.positive_charge,
            }
            for b in m.batteries
        ],
        circuits=[
            {"id": c.id, "name": c.name, "power": c.power, "group": c.group, "icon": c.icon, "in_total": c.in_total} for c in m.circuits
        ],
        zones=[{"id": z.id, "name": z.name, "valve": z.valve, "soil": z.soil} for z in m.zones],
        lights=lights,
        climates=manager.climate_entities(),
        temperatures=manager.temperature_entities(),
        humidities=manager.humidity_entities(),
        gas=dict(manager.gas_entities),
    )


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _dashboards(hass: HomeAssistant) -> dict[str | None, Any] | None:
    data = hass.data.get("lovelace")
    if data is None:
        return None
    return data.dashboards if hasattr(data, "dashboards") else data["dashboards"]


STATIC_URL = f"/{DOMAIN}_static"
PANEL_ELEMENT = "centro-control-panel"


async def _async_register_static(hass: HomeAssistant) -> bool:
    """Serve the panel's JavaScript once per Home Assistant run."""
    if hass.data.get(f"{DOMAIN}_static"):
        return True
    if getattr(hass, "http", None) is None:
        return False
    from homeassistant.components.http import StaticPathConfig

    folder = Path(__file__).parent / "frontend"
    await hass.http.async_register_static_paths([StaticPathConfig(STATIC_URL, str(folder), False)])
    hass.data[f"{DOMAIN}_static"] = True
    return True


def panel_config(hass: HomeAssistant, entry: CentroConfigEntry) -> dict[str, Any]:
    ctx = asdict(build_context(hass, entry.runtime_data))
    ctx.update({"version": VERSION, "author": AUTHOR, "author_url": AUTHOR_URL, "repo_url": REPO_URL})
    return {
        "_panel_custom": {
            "name": PANEL_ELEMENT,
            "module_url": f"{STATIC_URL}/centro-control-panel.js?v={VERSION}",
            "embed_iframe": False,
            "trust_external": False,
        },
        "ctx": ctx,
    }


async def async_setup_dashboard(hass: HomeAssistant, entry: CentroConfigEntry, force: bool = False) -> None:
    """Register the Centro de Control panel in the sidebar (and keep a Lovelace copy on disk)."""
    url = dashboard_url(hass, entry)
    path = panel_path(hass, entry.entry_id)
    context = build_context(hass, entry.runtime_data)
    # A Lovelace version with HACS cards stays in config/centro_control/ for whoever prefers it.
    await hass.async_add_executor_job(_write, path, dump(build_panel(context, url)))

    if not await _async_register_static(hass):
        _LOGGER.warning("HTTP no está disponible; no se puede registrar el panel")
        return
    ours: set[str] = hass.data.setdefault(_OURS, set())
    if url not in ours and frontend.async_panel_exists(hass, url):
        _notify(hass, entry, url, path)
        return
    dashboards = _dashboards(hass)
    if dashboards is not None and url in dashboards and url in ours:
        dashboards.pop(url, None)  # Lovelace panel of version 1.1 in this same run
    try:
        frontend.async_register_built_in_panel(
            hass,
            component_name="custom",
            sidebar_title=entry.title,
            sidebar_icon=DASHBOARD_ICON,
            frontend_url_path=url,
            config=panel_config(hass, entry),
            require_admin=False,
            update=url in ours or force,
        )
    except Exception:  # noqa: BLE001 - never break the integration for the panel
        _LOGGER.exception("No se pudo registrar el panel")
        _notify(hass, entry, url, path)
        return
    ours.add(url)


@callback
def async_remove_dashboard(hass: HomeAssistant, entry: CentroConfigEntry) -> None:
    """Take the dashboard out of the sidebar (the YAML file stays)."""
    url = dashboard_url(hass, entry)
    ours: set[str] = hass.data.get(_OURS, set())
    if url not in ours:
        return
    ours.discard(url)
    try:
        frontend.async_remove_panel(hass, url, warn_if_unknown=False)
    except TypeError:  # Home Assistant before warn_if_unknown existed
        frontend.async_remove_panel(hass, url)
    if (dashboards := _dashboards(hass)) is not None:
        dashboards.pop(url, None)


@callback
def _notify(hass: HomeAssistant, entry: CentroConfigEntry, url: str, path: Path) -> None:
    persistent_notification.async_create(
        hass,
        (
            f"Ya existe otro panel en `/{url}`, así que no lo he sustituido. "
            "Bórralo (Ajustes → Paneles) y pulsa «Regenerar panel». Mientras, tienes una "
            f"versión con tarjetas de Lovelace en `{path}`."
        ),
        title="Centro de Control",
        notification_id=f"{DOMAIN}_{entry.entry_id}_panel",
    )
