"""Buttons: acknowledge problems, lights off, irrigation and rebuild the panel."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import SUB_ZONE
from .entity import CentroEntity
from .manager import CentroConfigEntry, CentroManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CentroConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    manager = entry.runtime_data
    buttons: list[ButtonEntity] = [Acknowledge(manager), LightsOff(manager), RebuildPanel(manager)]
    if manager.model.zones:
        buttons.append(StopAll(manager))
    async_add_entities(buttons)
    for sub_id, sub in entry.subentries.items():
        if sub.subentry_type == SUB_ZONE:
            async_add_entities([WaterZone(manager, sub_id, sub.title)], config_subentry_id=sub_id)


class Acknowledge(CentroEntity, ButtonEntity):
    _attr_icon = "mdi:check-all"

    def __init__(self, manager: CentroManager) -> None:
        super().__init__(manager, "reconocer_problemas")

    async def async_press(self) -> None:
        self.coordinator.acknowledge()


class LightsOff(CentroEntity, ButtonEntity):
    _attr_icon = "mdi:lightbulb-group-off"

    def __init__(self, manager: CentroManager) -> None:
        super().__init__(manager, "apagar_luces")

    async def async_press(self) -> None:
        lights = [e for e in self.coordinator.light_entities() if (st := self.hass.states.get(e)) and st.state == "on"]
        if lights:
            await self.hass.services.async_call("light", "turn_off", {"entity_id": lights}, blocking=True)


class RebuildPanel(CentroEntity, ButtonEntity):
    _attr_icon = "mdi:view-dashboard-edit"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, manager: CentroManager) -> None:
        super().__init__(manager, "regenerar_panel")

    async def async_press(self) -> None:
        from .dashboard import async_setup_dashboard

        await async_setup_dashboard(self.hass, self.coordinator.config_entry, force=True)


class StopAll(CentroEntity, ButtonEntity):
    _attr_icon = "mdi:water-off"

    def __init__(self, manager: CentroManager) -> None:
        super().__init__(manager, "parar_riego")

    async def async_press(self) -> None:
        await self.coordinator.async_stop_all()


class WaterZone(CentroEntity, ButtonEntity):
    _attr_icon = "mdi:sprinkler"

    def __init__(self, manager: CentroManager, sub_id: str, title: str) -> None:
        super().__init__(manager, "regar", sub_id, title, "Zona de riego")

    async def async_press(self) -> None:
        await self.coordinator.async_start_zone(self.subentry_id or "")
