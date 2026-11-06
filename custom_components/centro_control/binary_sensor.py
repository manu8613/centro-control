"""Binary sensors for Centro de Control."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import CentroEntity
from .manager import CentroConfigEntry, CentroManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CentroConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    manager = entry.runtime_data
    entities: list[BinarySensorEntity] = [CriticalProblem(manager)]
    if manager.model.zones:
        entities.append(Watering(manager))
    async_add_entities(entities)


class CriticalProblem(CentroEntity, BinarySensorEntity):
    """On while there is an unacknowledged critical problem."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, manager: CentroManager) -> None:
        super().__init__(manager, "problema_critico")

    @property
    def is_on(self) -> bool:
        return any(p["nivel"] == "critico" and not p["reconocido"] for p in self.coordinator.problems)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"titulos": [p["titulo"] for p in self.coordinator.problems if p["nivel"] == "critico"]}


class Watering(CentroEntity, BinarySensorEntity):
    """On while any irrigation valve is open."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_icon = "mdi:sprinkler-variant"

    def __init__(self, manager: CentroManager) -> None:
        super().__init__(manager, "riego_activo")

    @property
    def is_on(self) -> bool:
        m = self.coordinator
        return any((st := m.hass.states.get(z.valve)) is not None and st.state in ("on", "open", "opening") for z in m.model.zones)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        m = self.coordinator
        return {"lloviendo": m.raining(), "omitir_si_llueve": m.skip_rain}
