"""HTTP API for backups, inventory and remote configuration (admin only).

Lets a script with a long-lived token of an administrator:

* ``GET  /api/centro_control/inventario``     everything needed to plan the
  configuration: states, entity/device/area registries, Energy dashboard
  preferences, Lovelace dashboards and integrations.
* ``GET  /api/centro_control/configuracion``  the current configuration of every
  Centro de Control (options + strings, batteries, circuits and zones).
* ``POST /api/centro_control/configuracion``  apply a configuration in that
  same format. The current one is saved first in
  ``config/centro_control/copias/``; ``"simular": true`` only checks it.
  Posting a saved copy restores it.
"""

from __future__ import annotations

from datetime import datetime
from http import HTTPStatus
import json
import logging
from pathlib import Path
from typing import Any

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import __version__ as HA_VERSION
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er

from .const import DOMAIN, SUBENTRY_TYPES, VERSION

_LOGGER = logging.getLogger(__name__)

KEEP_ATTRS = (
    "friendly_name",
    "unit_of_measurement",
    "device_class",
    "state_class",
    "supported_color_modes",
    "hvac_modes",
    "options",
    "restored",
    "icon",
)


def backups_dir(hass: HomeAssistant) -> Path:
    return Path(hass.config.path(DOMAIN, "copias"))


def current_config(hass: HomeAssistant) -> dict[str, Any]:
    return {
        "formato": "centro_control/1",
        "version": VERSION,
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "entradas": [_entry_dict(e) for e in hass.config_entries.async_entries(DOMAIN)],
    }


def _entry_dict(entry: ConfigEntry) -> dict[str, Any]:
    return {
        "entry_id": entry.entry_id,
        "titulo": entry.title,
        "opciones": dict(entry.options),
        "elementos": [
            {"tipo": s.subentry_type, "titulo": s.title, "datos": dict(s.data)}
            for s in sorted(entry.subentries.values(), key=lambda s: (s.subentry_type, s.title))
        ],
    }


def _write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _resolve_names(hass: HomeAssistant, data: Any, warnings: list[str], resolved: dict[str, str]) -> Any:
    """Replace ``"~[domain:]Entity name"`` with the entity id that has that name.

    Lets a plan point at entities whose id is not known in advance (e.g. the
    ones a new ESPHome device has just created). Names that match no entity,
    or more than one, are dropped with a warning.
    """
    if isinstance(data, dict):
        out = {}
        for key, value in data.items():
            new = _resolve_names(hass, value, warnings, resolved)
            if new is not None:
                out[key] = new
        return out
    if isinstance(data, list):
        return [v for v in (_resolve_names(hass, v, warnings, resolved) for v in data) if v is not None]
    if not (isinstance(data, str) and data.startswith("~")):
        return data
    wanted = data[1:].strip()
    domain = None
    if ":" in wanted and wanted.split(":", 1)[0].isidentifier():
        domain, wanted = wanted.split(":", 1)
    target = wanted.strip().casefold()
    matches: set[str] = set()
    for entry in er.async_get(hass).entities.values():
        if domain and entry.domain != domain:
            continue
        names = {n.casefold() for n in (entry.name, entry.original_name) if n}
        if target in names:
            matches.add(entry.entity_id)
    if not matches:
        for state in hass.states.async_all(domain) if domain else hass.states.async_all():
            if str(state.attributes.get("friendly_name", "")).casefold() == target:
                matches.add(state.entity_id)
    if len(matches) == 1:
        resolved[data] = next(iter(matches))
        return resolved[data]
    if matches:
        warnings.append(f"«{wanted}» coincide con varias entidades ({', '.join(sorted(matches))}): no se usa")
    else:
        warnings.append(f"No hay ninguna entidad llamada «{wanted}»: no se usa")
    return None


def _referenced(data: Any) -> set[str]:
    """Every value that looks like an entity id."""
    found: set[str] = set()
    if isinstance(data, str):
        if data.count(".") == 1 and " " not in data and data.split(".")[0].isidentifier():
            found.add(data)
    elif isinstance(data, dict):
        for value in data.values():
            found |= _referenced(value)
    elif isinstance(data, list):
        for value in data:
            found |= _referenced(value)
    return found


class _Admin(HomeAssistantView):
    requires_auth = True

    def _check(self, request: web.Request) -> web.Response | None:
        user = request.get("hass_user")
        if user is None or not user.is_admin:
            return self.json_message("Solo un administrador puede usar esta API.", HTTPStatus.FORBIDDEN)
        return None


class InventoryView(_Admin):
    url = "/api/centro_control/inventario"
    name = "api:centro_control:inventario"

    async def get(self, request: web.Request) -> web.Response:
        if (denied := self._check(request)) is not None:
            return denied
        hass: HomeAssistant = request.app["hass"]
        ent = er.async_get(hass)
        dev = dr.async_get(hass)
        area = ar.async_get(hass)
        states = [
            {
                "entity_id": s.entity_id,
                "state": s.state,
                "attributes": {k: s.attributes[k] for k in KEEP_ATTRS if k in s.attributes},
            }
            for s in hass.states.async_all()
        ]
        entities = [
            {
                "entity_id": e.entity_id,
                "platform": e.platform,
                "device_id": e.device_id,
                "area_id": e.area_id,
                "name": e.name,
                "original_name": e.original_name,
                "entity_category": e.entity_category,
                "disabled_by": e.disabled_by,
                "hidden_by": e.hidden_by,
                "device_class": e.device_class or e.original_device_class,
                "unit": e.unit_of_measurement,
            }
            for e in ent.entities.values()
        ]
        devices = [
            {
                "id": d.id,
                "name": d.name_by_user or d.name,
                "manufacturer": d.manufacturer,
                "model": d.model,
                "area_id": d.area_id,
                "disabled_by": d.disabled_by,
            }
            for d in dev.devices.values()
        ]
        areas = [{"id": a.id, "name": a.name, "floor_id": a.floor_id} for a in area.async_list_areas()]
        energy: Any = None
        try:
            from homeassistant.components.energy.data import async_get_manager

            energy = (await async_get_manager(hass)).data
        except Exception as err:  # noqa: BLE001
            energy = {"error": str(err)}
        dashboards: dict[str, Any] = {}
        lovelace = hass.data.get("lovelace")
        boards = getattr(lovelace, "dashboards", None) if lovelace is not None else None
        for url, board in (boards or {}).items():
            try:
                dashboards[url or "lovelace"] = await board.async_load(False)
            except Exception as err:  # noqa: BLE001 - e.g. an empty default dashboard
                dashboards[url or "lovelace"] = {"error": str(err)}
        integrations = [
            {"domain": e.domain, "title": e.title, "entry_id": e.entry_id, "state": str(e.state)}
            for e in hass.config_entries.async_entries()
        ]
        return self.json(
            {
                "formato": "centro_control_inventario/1",
                "version": VERSION,
                "ha_version": HA_VERSION,
                "fecha": datetime.now().isoformat(timespec="seconds"),
                "zona_horaria": hass.config.time_zone,
                "estados": states,
                "entidades": entities,
                "dispositivos": devices,
                "areas": areas,
                "energia": energy,
                "paneles": dashboards,
                "integraciones": integrations,
                "centro_control": current_config(hass),
            }
        )


class ConfigView(_Admin):
    url = "/api/centro_control/configuracion"
    name = "api:centro_control:configuracion"

    async def get(self, request: web.Request) -> web.Response:
        if (denied := self._check(request)) is not None:
            return denied
        return self.json(current_config(request.app["hass"]))

    async def post(self, request: web.Request) -> web.Response:
        if (denied := self._check(request)) is not None:
            return denied
        hass: HomeAssistant = request.app["hass"]
        try:
            body = await request.json()
        except ValueError:
            return self.json_message("El cuerpo no es JSON.", HTTPStatus.BAD_REQUEST)
        simulate = bool(body.get("simular"))
        wanted = body.get("entradas") or []
        if not isinstance(wanted, list) or not wanted:
            return self.json_message("Falta la lista «entradas».", HTTPStatus.BAD_REQUEST)

        warnings: list[str] = []
        resolved: dict[str, str] = {}
        wanted = [_resolve_names(hass, item, warnings, resolved) for item in wanted]
        for item in wanted:
            for entity in sorted(_referenced({"o": item.get("opciones", {}), "e": item.get("elementos", [])})):
                if hass.states.get(entity) is None and not entity.startswith(("notify.", "persistent_notification")):
                    warnings.append(f"No existe {entity}")
            for element in item.get("elementos", []):
                if element.get("tipo") not in SUBENTRY_TYPES:
                    return self.json_message(f"Tipo de elemento desconocido: {element.get('tipo')}", HTTPStatus.BAD_REQUEST)
        if simulate:
            return self.json({"ok": True, "simulado": True, "avisos": warnings, "resueltas": resolved})

        backup = backups_dir(hass) / f"config_{datetime.now():%Y%m%d_%H%M%S}.json"
        await hass.async_add_executor_job(_write, backup, current_config(hass))

        applied = []
        imported: dict[str, int] = {}
        for item in wanted:
            entry = await self._entry_for(hass, item)
            await self._apply(hass, entry, item)
            applied.append(entry.entry_id)
            manager = getattr(entry, "runtime_data", None)
            if manager is None:
                continue
            if body.get("reiniciar_contadores"):
                manager.reset_counters()
                manager.imported = False
            if days := int(body.get("importar_historico") or 0):
                imported[entry.entry_id] = await manager.async_import_history(min(days, 800))
        return self.json({"ok": True, "copia": str(backup), "entradas": applied, "avisos": warnings, "resueltas": resolved, "dias_importados": imported})

    async def _entry_for(self, hass: HomeAssistant, item: dict[str, Any]) -> ConfigEntry:
        entries = hass.config_entries.async_entries(DOMAIN)
        if item.get("entry_id"):
            for entry in entries:
                if entry.entry_id == item["entry_id"]:
                    return entry
        if len(entries) == 1 and not item.get("nueva"):
            return entries[0]
        options = item.get("opciones", {})
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "nombre": item.get("titulo") or "Centro de Control",
                "red_potencia": options.get("red_potencia"),
                "red_signo": options.get("red_signo", "positivo_importa"),
                "crear_panel": options.get("crear_panel", True),
            },
        )
        return result["result"]

    async def _apply(self, hass: HomeAssistant, entry: ConfigEntry, item: dict[str, Any]) -> None:
        manager = hass.config_entries
        # Subentries: the ones with the same type and title are updated in
        # place (same id, so their entities, history and counters are kept);
        # new ones are added and the rest removed. Each change reloads, so do
        # it with the entry unloaded and reload once at the end.
        await manager.async_unload(entry.entry_id)
        existing = {(s.subentry_type, s.title): s for s in entry.subentries.values()}
        keep: set[str] = set()
        for element in item.get("elementos", []):
            title = str(element.get("titulo") or element.get("datos", {}).get("nombre") or element["tipo"])
            data = dict(element.get("datos", {}))
            current = existing.get((element["tipo"], title))
            if current is not None and current.subentry_id not in keep:
                keep.add(current.subentry_id)
                if dict(current.data) != data:
                    manager.async_update_subentry(entry, current, data=data)
                continue
            new = ConfigSubentry(data=data, subentry_type=element["tipo"], title=title, unique_id=None)
            manager.async_add_subentry(entry, new)
            keep.add(new.subentry_id)
        for sub_id in [s for s in entry.subentries if s not in keep]:
            manager.async_remove_subentry(entry, sub_id)
        manager.async_update_entry(
            entry,
            title=item.get("titulo") or entry.title,
            options=dict(item.get("opciones", entry.options)),
        )
        await manager.async_setup(entry.entry_id)


class StatusView(_Admin):
    """Short health report: our entities, the ones without data and the problems."""

    url = "/api/centro_control/estado"
    name = "api:centro_control:estado"

    async def get(self, request: web.Request) -> web.Response:
        if (denied := self._check(request)) is not None:
            return denied
        hass: HomeAssistant = request.app["hass"]
        ours = [e for e in er.async_get(hass).entities.values() if e.platform == DOMAIN and not e.disabled_by]
        missing = []
        for e in ours:
            state = hass.states.get(e.entity_id)
            if state is None or state.state in ("unavailable", "unknown"):
                missing.append(e.entity_id)
        entries = []
        for entry in hass.config_entries.async_entries(DOMAIN):
            manager = getattr(entry, "runtime_data", None)
            entries.append(
                {
                    "titulo": entry.title,
                    "estado": str(entry.state),
                    "elementos": len(entry.subentries),
                    "problemas": [
                        f"[{p['nivel']}] {p['area']}: {p['titulo']} — {p['detalle']}" for p in (manager.problems if manager else [])
                    ],
                    "solar_w": manager.live.get("pv_w") if manager else None,
                    "red_w": manager.live.get("grid_w") if manager else None,
                    "consumo_w": manager.live.get("load_w") if manager else None,
                    "bateria_w": manager.live.get("battery_w") if manager else None,
                    "soc": manager.live.get("soc") if manager else None,
                }
            )
        return self.json({"version": VERSION, "entidades": len(ours), "sin_dato": missing, "entradas": entries})


def async_register_api(hass: HomeAssistant) -> None:
    hass.http.register_view(InventoryView())
    hass.http.register_view(ConfigView())
    hass.http.register_view(StatusView())
