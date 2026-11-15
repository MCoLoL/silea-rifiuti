"""Coordinator: scarica i mesi pubblicati e li trasforma in ritiri."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
import hashlib
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import SileaApi, SileaError
from .const import (
    CONF_COMUNE,
    CONF_MESI,
    CONF_VIA,
    DEFAULT_END,
    DEFAULT_MESI,
    DEFAULT_START,
    DOMAIN,
    MAX_OFFSET_MINUTES,
    TIPI,
    UPDATE_INTERVAL,
    tipo_da_servizio,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class Ritiro:
    """Un passaggio di raccolta: un tipo di rifiuto in un giorno."""

    giorno: date
    tipo: str
    servizio: str
    inizio: datetime
    fine: datetime
    note: str

    @property
    def nome(self) -> str:
        return TIPI.get(self.tipo, (self.servizio.capitalize(), ""))[0]


def _intervallo(entry_id: str) -> timedelta:
    """12 ore più uno scarto stabile ricavato dalla config entry."""
    scarto = int(hashlib.sha256(entry_id.encode()).hexdigest(), 16) % MAX_OFFSET_MINUTES
    return UPDATE_INTERVAL + timedelta(minutes=scarto)


def _ora(testo: str, default: str) -> time:
    try:
        h, m = (testo or default).strip().split(":")[:2]
        return time(int(h), int(m))
    except ValueError:
        h, m = default.split(":")
        return time(int(h), int(m))


def converti(giorni: list[dict]) -> list[Ritiro]:
    """Converte la risposta di get_calendar in una lista di Ritiro."""
    tz = dt_util.get_default_time_zone()
    out: list[Ritiro] = []
    for g in giorni:
        try:
            giorno = date.fromisoformat(str(g.get("format", ""))[:10])
        except ValueError:
            continue
        for s in g.get("services") or []:
            servizio = str(s.get("service") or "").strip()
            if not servizio:
                continue
            ore = str(s.get("hours") or "").split("-")
            inizio = _ora(ore[0] if ore else "", DEFAULT_START)
            fine = _ora(ore[1] if len(ore) > 1 else "", DEFAULT_END)
            out.append(
                Ritiro(
                    giorno=giorno,
                    tipo=tipo_da_servizio(servizio),
                    servizio=servizio,
                    inizio=datetime.combine(giorno, inizio, tz),
                    fine=datetime.combine(giorno, fine, tz),
                    note=str(s.get("notes") or "").strip(),
                )
            )
    return out


class SileaCoordinator(DataUpdateCoordinator[list[Ritiro]]):
    """Aggiorna il calendario due volte al giorno."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=_intervallo(entry.entry_id), config_entry=entry
        )
        self.api = SileaApi(async_get_clientsession(hass))
        self.comune = entry.data[CONF_COMUNE]
        self.via = entry.data[CONF_VIA]

    async def _async_update_data(self) -> list[Ritiro]:
        n_mesi = int(self.config_entry.options.get(CONF_MESI, DEFAULT_MESI))
        try:
            mesi = (await self.api.mesi(self.comune, self.via))[:n_mesi]
            ritiri: dict[tuple[date, str], Ritiro] = {}
            for mese in mesi:
                for r in converti(await self.api.calendario(self.comune, self.via, mese)):
                    ritiri[(r.giorno, r.tipo)] = r
        except SileaError as err:
            raise UpdateFailed(f"Sito Silea non raggiungibile: {err}") from err
        if not ritiri and self.data:
            raise UpdateFailed("Il sito Silea non ha restituito ritiri")
        return sorted(ritiri.values(), key=lambda r: (r.inizio, list(TIPI).index(r.tipo) if r.tipo in TIPI else 99))

    def prossimi(self, adesso: datetime | None = None) -> list[Ritiro]:
        """Ritiri non ancora conclusi (quelli di oggi contano fino all'ora di fine)."""
        adesso = adesso or dt_util.now()
        return [r for r in self.data or [] if r.fine > adesso]
