"""Entità base: un dispositivo 'servizio' per ogni indirizzo configurato."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_COMUNE_NOME, CONF_VIA_NOME, DOMAIN
from .coordinator import SileaCoordinator


class SileaEntity(CoordinatorEntity[SileaCoordinator]):
    _attr_has_entity_name = True
    _attr_attribution = "Dati da sileaspa.it"

    def __init__(self, coordinator: SileaCoordinator, chiave: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{chiave}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Raccolta rifiuti {entry.data.get(CONF_VIA_NOME, '')}".strip(),
            manufacturer="Silea S.p.A.",
            model=entry.data.get(CONF_COMUNE_NOME),
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://www.sileaspa.it/calendario-raccolta-rifiuti/",
        )

    async def async_added_to_hass(self) -> None:
        """Oltre agli aggiornamenti dal sito, ricalcola lo stato ogni 5 minuti (giorni mancanti, ritiro di oggi concluso)."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_interval(self.hass, self._tick, timedelta(minutes=5))
        )

    @callback
    def _tick(self, _now: datetime) -> None:
        self.async_write_ha_state()
