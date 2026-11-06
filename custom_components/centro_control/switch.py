"""Switch: skip irrigation while it rains."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import CentroEntity
from .manager import CentroConfigEntry, CentroManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CentroConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    if entry.runtime_data.model.zones:
        async_add_entities([SkipRain(entry.runtime_data)])


class SkipRain(CentroEntity, SwitchEntity):
    _attr_icon = "mdi:weather-pouring"

    def __init__(self, manager: CentroManager) -> None:
        super().__init__(manager, "omitir_si_llueve")

    @property
    def is_on(self) -> bool:
        return self.coordinator.skip_rain

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.coordinator.set_skip_rain(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.coordinator.set_skip_rain(False)
