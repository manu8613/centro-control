"""Numbers: the bill simulator and the irrigation time of each zone."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.const import PERCENTAGE, UnitOfPower, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import SUB_ZONE
from .entity import CentroEntity
from .manager import SIM_DEFAULTS, CentroConfigEntry, CentroManager


@dataclass(frozen=True, kw_only=True)
class SimDescription(NumberEntityDescription):
    pass


SIM: tuple[SimDescription, ...] = (
    SimDescription(
        key="sim_potencia_p1",
        native_min_value=-1,
        native_max_value=15,
        native_step=0.05,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        icon="mdi:flash-triangle",
        mode=NumberMode.BOX,
    ),
    SimDescription(
        key="sim_potencia_p2",
        native_min_value=-1,
        native_max_value=15,
        native_step=0.05,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        icon="mdi:flash-triangle-outline",
        mode=NumberMode.BOX,
    ),
    SimDescription(
        key="sim_consumo",
        native_min_value=-50,
        native_max_value=100,
        native_step=5,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:home-lightning-bolt",
        mode=NumberMode.SLIDER,
    ),
    SimDescription(
        key="sim_precio",
        native_min_value=-50,
        native_max_value=100,
        native_step=5,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:cash-multiple",
        mode=NumberMode.SLIDER,
    ),
    SimDescription(
        key="sim_paneles",
        native_min_value=0,
        native_max_value=20000,
        native_step=100,
        native_unit_of_measurement="Wp",
        icon="mdi:solar-panel-large",
        mode=NumberMode.SLIDER,
    ),
    SimDescription(
        key="sim_bateria",
        native_min_value=0,
        native_max_value=60,
        native_step=1,
        native_unit_of_measurement="kWh",
        icon="mdi:battery-plus",
        mode=NumberMode.SLIDER,
    ),
    SimDescription(
        key="sim_excedentes",
        native_min_value=-1,
        native_max_value=0.5,
        native_step=0.005,
        native_unit_of_measurement="€/kWh",
        icon="mdi:transmission-tower-export",
        mode=NumberMode.BOX,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CentroConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    manager = entry.runtime_data
    async_add_entities(SimNumber(manager, d) for d in SIM)
    for sub_id, sub in entry.subentries.items():
        if sub.subentry_type == SUB_ZONE:
            async_add_entities([ZoneMinutes(manager, sub_id, sub.title)], config_subentry_id=sub_id)


class SimNumber(CentroEntity, NumberEntity):
    """What-if value for the bill simulator (-1 = as in the contract)."""

    entity_description: SimDescription

    def __init__(self, manager: CentroManager, description: SimDescription) -> None:
        super().__init__(manager, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float:
        return self.coordinator.sim.get(self.entity_description.key, SIM_DEFAULTS[self.entity_description.key])

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.set_sim(self.entity_description.key, float(value))


class ZoneMinutes(CentroEntity, NumberEntity):
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_native_min_value = 1
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:timer-cog-outline"

    def __init__(self, manager: CentroManager, sub_id: str, title: str) -> None:
        super().__init__(manager, "minutos_riego", sub_id, title, "Zona de riego")
        zone = next(z for z in manager.model.zones if z.id == sub_id)
        self._attr_native_max_value = zone.max_minutes

    @property
    def native_value(self) -> float:
        return self.coordinator.zone_minutes.get(self.subentry_id or "", 10.0)

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.set_zone_minutes(self.subentry_id or "", float(value))
