"""Centro di raccolta aperto o chiuso, con orari e prossima apertura negli attributi."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import SileaConfigEntry
from .coordinator import SileaCoordinator
from .entity import CentroEntity, aggiungi_centro


async def async_setup_entry(
    hass: HomeAssistant, entry: SileaConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    aggiungi_centro(coordinator, async_add_entities, lambda: [CentroAperto(coordinator)])


class CentroAperto(CentroEntity, BinarySensorEntity):
    """Acceso quando il centro di raccolta del comune è aperto, secondo gli orari Silea."""

    _attr_translation_key = "centro_aperto"
    _attr_device_class = BinarySensorDeviceClass.OPENING
    _attr_icon = "mdi:store-outline"

    def __init__(self, coordinator: SileaCoordinator) -> None:
        super().__init__(coordinator, "centro_aperto")

    @property
    def is_on(self) -> bool | None:
        c = self.centro
        return c.in_corso(dt_util.now()) is not None if c else None
