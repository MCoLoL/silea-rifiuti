"""Sensori: prossimo ritiro, cosa esporre stasera e prossimo passaggio per ogni tipo."""

from __future__ import annotations

from datetime import date
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import SileaConfigEntry
from .const import TIPI
from .coordinator import Ritiro, SileaCoordinator
from .entity import SileaEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: SileaConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    tipi = list(TIPI) + sorted({r.tipo for r in coordinator.data or []} - set(TIPI))
    entities: list[SensorEntity] = [
        ProssimoRitiro(coordinator),
        DaEsporre(coordinator),
    ]
    entities += [ProssimoPerTipo(coordinator, t) for t in tipi]
    async_add_entities(entities)


def _giorni(d: date) -> int:
    return (d - dt_util.now().date()).days


class ProssimoRitiro(SileaEntity, SensorEntity):
    """Data del prossimo ritiro, con i tipi di rifiuto negli attributi."""

    _attr_translation_key = "prossimo_ritiro"
    _attr_device_class = SensorDeviceClass.DATE
    _attr_icon = "mdi:calendar-arrow-right"

    def __init__(self, coordinator: SileaCoordinator) -> None:
        super().__init__(coordinator, "prossimo_ritiro")

    def _giorno(self) -> list[Ritiro]:
        prossimi = self.coordinator.prossimi()
        return [r for r in prossimi if r.giorno == prossimi[0].giorno] if prossimi else []

    @property
    def native_value(self) -> date | None:
        g = self._giorno()
        return g[0].giorno if g else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        g = self._giorno()
        if not g:
            return {}
        return {
            "tipi": [r.nome for r in g],
            "chiavi": [r.tipo for r in g],
            "giorni": _giorni(g[0].giorno),
            "inizio": g[0].inizio.isoformat(),
            "fine": g[0].fine.isoformat(),
            "note": g[0].note,
        }


class DaEsporre(SileaEntity, SensorEntity):
    """Cosa portare fuori: i ritiri di domani (o di oggi, finché non sono conclusi)."""

    _attr_translation_key = "da_esporre"
    _attr_icon = "mdi:delete-clock-outline"

    def __init__(self, coordinator: SileaCoordinator) -> None:
        super().__init__(coordinator, "da_esporre")

    def _lista(self) -> list[Ritiro]:
        oggi = dt_util.now().date()
        return [r for r in self.coordinator.prossimi() if 0 <= (r.giorno - oggi).days <= 1]

    @property
    def native_value(self) -> str:
        lst = self._lista()
        if not lst:
            return "Niente"
        return ", ".join(r.nome for r in lst)[:255]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        lst = self._lista()
        return {
            "tipi": [r.nome for r in lst],
            "chiavi": [r.tipo for r in lst],
            "giorno": lst[0].giorno.isoformat() if lst else None,
            "quando": ("oggi" if lst and lst[0].giorno == dt_util.now().date() else "domani") if lst else None,
            "note": lst[0].note if lst else None,
        }


class ProssimoPerTipo(SileaEntity, SensorEntity):
    """Data del prossimo passaggio di un tipo di rifiuto."""

    _attr_device_class = SensorDeviceClass.DATE

    def __init__(self, coordinator: SileaCoordinator, tipo: str) -> None:
        super().__init__(coordinator, f"prossimo_{tipo}")
        self._tipo = tipo
        if tipo in TIPI:
            self._attr_translation_key = f"prossimo_{tipo}"
            self._attr_icon = TIPI[tipo][1]
        else:
            self._attr_name = f"Prossimo {tipo.replace('_', ' ')}"
            self._attr_icon = "mdi:delete-outline"

    def _prossimo(self) -> Ritiro | None:
        return next((r for r in self.coordinator.prossimi() if r.tipo == self._tipo), None)

    @property
    def native_value(self) -> date | None:
        r = self._prossimo()
        return r.giorno if r else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        r = self._prossimo()
        return {"giorni": _giorni(r.giorno), "note": r.note} if r else {}
