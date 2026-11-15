"""Entità base: un dispositivo 'servizio' per ogni indirizzo configurato."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_point_in_time, async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .centri import DEFAULT_UTENZA, Centro, attributi, trova_centro
from .const import CONF_COMUNE, CONF_COMUNE_NOME, CONF_UTENZA, CONF_VIA_NOME, DOMAIN
from .coordinator import CentriCoordinator, SileaCoordinator

ATTRIBUTION = "Dati da sileaspa.it"


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=f"Raccolta rifiuti {entry.data.get(CONF_VIA_NOME, '')}".strip(),
        manufacturer="Silea S.p.A.",
        model=entry.data.get(CONF_COMUNE_NOME),
        entry_type=DeviceEntryType.SERVICE,
        configuration_url="https://www.sileaspa.it/calendario-raccolta-rifiuti/",
    )


class SileaEntity(CoordinatorEntity[SileaCoordinator]):
    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(self, coordinator: SileaCoordinator, chiave: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{chiave}"
        self._attr_device_info = _device_info(entry)

    async def async_added_to_hass(self) -> None:
        """Oltre agli aggiornamenti dal sito, ricalcola lo stato ogni 5 minuti (giorni mancanti, ritiro di oggi concluso)."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_interval(self.hass, self._tick, timedelta(minutes=5))
        )

    @callback
    def _tick(self, _now: datetime) -> None:
        self.async_write_ha_state()


def _centro(entry: ConfigEntry, dati: list[dict[str, Any]] | None) -> Centro | None:
    return trova_centro(dati or [], entry.data[CONF_COMUNE], entry.options.get(CONF_UTENZA, DEFAULT_UTENZA))


class CentroEntity(CoordinatorEntity[CentriCoordinator]):
    """Entità del centro di raccolta che serve il comune; sta nel dispositivo della via."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(self, coordinator: SileaCoordinator, chiave: str) -> None:
        assert coordinator.centri is not None
        super().__init__(coordinator.centri)
        self._entry = coordinator.config_entry
        self._attr_unique_id = f"{self._entry.entry_id}_{chiave}"
        self._attr_device_info = _device_info(self._entry)
        self._timer: CALLBACK_TYPE | None = None
        self._cache: tuple[object, Centro | None] = (None, None)

    @property
    def centro(self) -> Centro | None:
        dati = self.coordinator.data
        if self._cache[0] is not dati:
            self._cache = (dati, _centro(self._entry, dati))
        return self._cache[1]

    @property
    def available(self) -> bool:
        # Se un aggiornamento fallisce restano validi gli orari già scaricati.
        return self.centro is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        c = self.centro
        return attributi(c, dt_util.now()) if c else {}

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self._annulla)
        self._programma()

    @callback
    def _annulla(self) -> None:
        if self._timer:
            self._timer()
            self._timer = None

    @callback
    def _programma(self) -> None:
        """Ricalcola lo stato esattamente alla prossima apertura o chiusura (e a mezzanotte)."""
        self._annulla()
        c = self.centro
        if c is not None:
            self._timer = async_track_point_in_time(self.hass, self._scatta, c.prossimo_cambio(dt_util.now()))

    @callback
    def _scatta(self, _now: datetime) -> None:
        self._timer = None
        self.async_write_ha_state()
        self._programma()

    @callback
    def _handle_coordinator_update(self) -> None:
        super()._handle_coordinator_update()
        self._programma()


def aggiungi_centro(
    coordinator: SileaCoordinator,
    async_add_entities: AddEntitiesCallback,
    crea: Callable[[], list[Entity]],
) -> None:
    """Aggiunge le entità del centro di raccolta, subito o appena arrivano i dati dal sito.

    Se il comune non ha un centro di raccolta Silea non aggiunge nulla.
    """
    centri = coordinator.centri
    entry = coordinator.config_entry
    if centri is None:
        return
    if centri.data is not None:
        if _centro(entry, centri.data):
            async_add_entities(crea())
        return

    rimuovi: CALLBACK_TYPE | None = None

    @callback
    def _stacca() -> None:
        nonlocal rimuovi
        if rimuovi:
            rimuovi()
            rimuovi = None

    @callback
    def _arrivati() -> None:
        if centri.data is None:
            return
        _stacca()
        if _centro(entry, centri.data):
            async_add_entities(crea())

    rimuovi = centri.async_add_listener(_arrivati)
    entry.async_on_unload(_stacca)
