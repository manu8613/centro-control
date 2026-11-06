"""Centro de Control: a futuristic control room for your home in Home Assistant.

Created by manu8613 — https://github.com/manu8613/centro-control
"""

from __future__ import annotations

import logging

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.typing import ConfigType

from .const import AUTHOR, CONF_CREATE_DASHBOARD, DOMAIN, NAME, REPO_URL, VERSION
from .dashboard import async_remove_dashboard, async_setup_dashboard, remove_panel_file
from .manager import CentroConfigEntry, CentroManager
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.BUTTON,
    Platform.SWITCH,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: CentroConfigEntry) -> bool:
    manager = CentroManager(hass, entry)
    await manager.async_load()
    entry.runtime_data = manager
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer=AUTHOR,
        model=NAME,
        sw_version=VERSION,
        entry_type=dr.DeviceEntryType.SERVICE,
        configuration_url=REPO_URL,
    )
    manager.async_start()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    if entry.options.get(CONF_CREATE_DASHBOARD, True):
        await async_setup_dashboard(hass, entry)

        async def _rebuild(_hass: HomeAssistant) -> None:
            # Lights, thermometers... of other integrations exist once Home Assistant has started.
            await async_setup_dashboard(hass, entry, force=True)

        entry.async_on_unload(async_at_started(hass, _rebuild))
    return True


async def _async_reload(hass: HomeAssistant, entry: CentroConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: CentroConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        manager = entry.runtime_data
        manager.async_stop()
        await manager.async_flush()
        async_remove_dashboard(hass, entry)
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: CentroConfigEntry) -> None:
    from homeassistant.helpers.storage import Store

    from .const import STORAGE_VERSION

    await Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}").async_remove()
    await hass.async_add_executor_job(remove_panel_file, hass, entry.entry_id)
