"""Calendario della raccolta: un evento per ogni tipo di rifiuto ritirato."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SileaConfigEntry
from .coordinator import Ritiro
from .entity import SileaEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: SileaConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([SileaCalendar(entry.runtime_data)])


def _evento(r: Ritiro) -> CalendarEvent:
    descr = r.note or ""
    if r.servizio.upper() != r.nome.upper():
        descr = f"{r.servizio}. {descr}".strip()
    return CalendarEvent(
        start=r.inizio,
        end=r.fine,
        summary=r.nome,
        description=descr or None,
        uid=f"silea-{r.giorno.isoformat()}-{r.tipo}",
    )


class SileaCalendar(SileaEntity, CalendarEntity):
    _attr_translation_key = "raccolta"
    _attr_icon = "mdi:delete-variant"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "calendario")

    @property
    def event(self) -> CalendarEvent | None:
        prossimi = self.coordinator.prossimi()
        return _evento(prossimi[0]) if prossimi else None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        return [
            _evento(r)
            for r in self.coordinator.data or []
            if r.fine > start_date and r.inizio < end_date
        ]
