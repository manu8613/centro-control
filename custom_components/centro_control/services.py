"""Actions (services) of Centro de Control."""

from __future__ import annotations

from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
import homeassistant.helpers.config_validation as cv

from .compat import vol
from .const import DOMAIN
from .manager import CentroManager

ENTRY = "config_entry_id"

_BASE = {vol.Optional(ENTRY): cv.string}
SCHEMA_WATER = vol.Schema({**_BASE, vol.Required("zona"): cv.string, vol.Optional("minutos"): vol.Coerce(float)})
SCHEMA_STOP = vol.Schema({**_BASE, vol.Optional("zona"): cv.string})
SCHEMA_PLAIN = vol.Schema(_BASE)
SCHEMA_RESET = vol.Schema({**_BASE, vol.Required("confirmar"): cv.boolean})


def _manager(hass: HomeAssistant, call: ServiceCall) -> CentroManager:
    entries = [e for e in hass.config_entries.async_entries(DOMAIN) if getattr(e, "runtime_data", None) is not None]
    wanted = call.data.get(ENTRY)
    for entry in entries:
        if wanted in (None, entry.entry_id):
            return entry.runtime_data
    raise ServiceValidationError("No hay ningún Centro de Control cargado con ese identificador.")


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    async def water(call: ServiceCall) -> None:
        manager = _manager(hass, call)
        if not await manager.async_start_zone(call.data["zona"], call.data.get("minutos")):
            raise ServiceValidationError(f"No se ha podido regar «{call.data['zona']}» (no existe o está lloviendo).")

    async def stop(call: ServiceCall) -> None:
        manager = _manager(hass, call)
        if zone := call.data.get("zona"):
            await manager.async_stop_zone(zone)
        else:
            await manager.async_stop_all()

    async def acknowledge(call: ServiceCall) -> None:
        _manager(hass, call).acknowledge()

    async def panel(call: ServiceCall) -> None:
        from .dashboard import async_setup_dashboard

        manager = _manager(hass, call)
        await async_setup_dashboard(hass, manager.config_entry, force=True)

    async def reset(call: ServiceCall) -> None:
        if not call.data["confirmar"]:
            raise ServiceValidationError("Marca «confirmar» para borrar los contadores.")
        _manager(hass, call).reset_counters()

    hass.services.async_register(DOMAIN, "regar", water, schema=SCHEMA_WATER)
    hass.services.async_register(DOMAIN, "parar_riego", stop, schema=SCHEMA_STOP)
    hass.services.async_register(DOMAIN, "reconocer_problemas", acknowledge, schema=SCHEMA_PLAIN)
    hass.services.async_register(DOMAIN, "crear_panel", panel, schema=SCHEMA_PLAIN)
    hass.services.async_register(DOMAIN, "reiniciar_contadores", reset, schema=SCHEMA_RESET)
