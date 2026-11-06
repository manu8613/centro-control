"""Base entity for Centro de Control."""

from __future__ import annotations

from homeassistant.const import MATCH_ALL
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import AUTHOR, DOMAIN, NAME, REPO_URL, VERSION
from .manager import CentroManager


class CentroEntity(CoordinatorEntity[CentroManager]):
    """Entity of the main device, or of one string/circuit/zone device."""

    _attr_has_entity_name = True
    # Attributes are big (lists, history, buckets) and change often: keep them
    # out of the recorder database.
    _unrecorded_attributes = frozenset({MATCH_ALL})

    def __init__(
        self,
        manager: CentroManager,
        key: str,
        subentry_id: str | None = None,
        subentry_name: str | None = None,
        model: str | None = None,
    ) -> None:
        super().__init__(manager)
        entry = manager.config_entry
        self.subentry_id = subentry_id
        self._attr_translation_key = key
        if subentry_id is None:
            self._attr_unique_id = f"{entry.entry_id}_{key}"
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, entry.entry_id)},
                name=entry.title,
                manufacturer=AUTHOR,
                model=NAME,
                sw_version=VERSION,
                entry_type=DeviceEntryType.SERVICE,
                configuration_url=REPO_URL,
            )
        else:
            self._attr_unique_id = f"{entry.entry_id}_{subentry_id}_{key}"
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, f"{entry.entry_id}_{subentry_id}")},
                name=subentry_name,
                manufacturer=AUTHOR,
                model=model or NAME,
                sw_version=VERSION,
                entry_type=DeviceEntryType.SERVICE,
                via_device=(DOMAIN, entry.entry_id),
            )
