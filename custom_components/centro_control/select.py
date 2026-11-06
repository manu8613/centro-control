"""Select entities: the period shown in the panel."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import PERIODS
from .entity import CentroEntity
from .manager import CentroConfigEntry, CentroManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CentroConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([PeriodSelect(entry.runtime_data)])


class PeriodSelect(CentroEntity, SelectEntity):
    """Which period the energy figures of the panel refer to."""

    _attr_options = list(PERIODS)
    _attr_icon = "mdi:calendar-range"

    def __init__(self, manager: CentroManager) -> None:
        super().__init__(manager, "periodo")

    @property
    def current_option(self) -> str:
        return self.coordinator.period

    async def async_select_option(self, option: str) -> None:
        self.coordinator.set_period(option)
