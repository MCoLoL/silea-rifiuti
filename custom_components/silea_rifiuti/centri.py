"""Centri di raccolta (riciclerie): orari di apertura pubblicati da Silea.

Solo logica sui dati, senza dipendenze da Home Assistant: si prova anche da sola.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any

GIORNI = ("lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica")
UTENZE = ("domestica", "non-domestica")
DEFAULT_UTENZA = "domestica"

# Per i nomi delle vie, che il sito scrive in maiuscolo.
_MINUSCOLE = {"a", "al", "alla", "alle", "ai", "da", "dal", "dalla", "de", "dei", "del", "della", "delle", "di", "e", "in", "per", "s."}

Fascia = tuple[time, time]


@dataclass(frozen=True)
class Periodo:
    """Un orario valido in un intervallo di date (per esempio l'orario invernale)."""

    nome: str
    descrizione: str
    dal: date
    al: date
    mensile: bool
    fasce: tuple[tuple[Fascia, ...], ...]  # 7 elementi, da lunedì a domenica

    def contiene(self, giorno: date) -> bool:
        return self.dal <= giorno <= self.al

    @property
    def etichetta(self) -> str:
        return f"{self.nome} ({self.descrizione[0].lower()}{self.descrizione[1:]})" if self.descrizione else self.nome


@dataclass(frozen=True)
class Centro:
    """Un centro di raccolta, con gli orari per un tipo di utenza."""

    id: str
    nome: str
    indirizzo: str
    latitudine: float | None
    longitudine: float | None
    comuni: tuple[str, ...]
    utenza: str
    periodi: tuple[Periodo, ...]

    def periodo(self, giorno: date) -> Periodo | None:
        """Il periodo settimanale valido quel giorno; se si sovrappongono, il più breve (il più specifico)."""
        validi = [p for p in self.periodi if not p.mensile and p.contiene(giorno)]
        return min(validi, key=lambda p: p.al - p.dal) if validi else None

    def solo_mensile(self, giorno: date) -> bool:
        """Quel giorno vale solo un orario mensile: il sito non dice in quali settimane."""
        return self.periodo(giorno) is None and any(p.mensile and p.contiene(giorno) for p in self.periodi)

    def fasce(self, giorno: date) -> tuple[Fascia, ...]:
        p = self.periodo(giorno)
        return p.fasce[giorno.weekday()] if p else ()

    def aperture(self, dal: datetime, giorni: int = 21) -> list[tuple[datetime, datetime]]:
        """Aperture che finiscono dopo `dal`, nei prossimi `giorni` giorni."""
        tz = dal.tzinfo
        out = []
        for n in range(giorni):
            g = dal.date() + timedelta(days=n)
            for inizio, fine in self.fasce(g):
                a, b = datetime.combine(g, inizio, tz), datetime.combine(g, fine, tz)
                if b > dal:
                    out.append((a, b))
        return out

    def in_corso(self, adesso: datetime) -> tuple[datetime, datetime] | None:
        return next((a for a in self.aperture(adesso, 1) if a[0] <= adesso), None)

    def prossima(self, adesso: datetime) -> tuple[datetime, datetime] | None:
        return next((a for a in self.aperture(adesso) if a[0] > adesso), None)

    def prossimo_cambio(self, adesso: datetime) -> datetime:
        """Quando ricalcolare lo stato: prossima apertura o chiusura, al più tardi mezzanotte."""
        mezzanotte = datetime.combine(adesso.date() + timedelta(days=1), time(0), adesso.tzinfo)
        istanti = [t for a in self.aperture(adesso, 2) for t in a if t > adesso]
        return min([*istanti, mezzanotte])

    def orario(self, giorno: date) -> dict[str, str]:
        """Orario della settimana valido quel giorno, come {'lunedì': 'chiuso', 'sabato': '08:00-12:00, ...'}."""
        p = self.periodo(giorno)
        if p is None:
            return {}
        return {GIORNI[i]: testo_fasce(f) for i, f in enumerate(p.fasce)}


def testo_fasce(fasce: tuple[Fascia, ...]) -> str:
    return ", ".join(f"{a:%H:%M}-{b:%H:%M}" for a, b in fasce) or "chiuso"


def _fascia(testo: str) -> Fascia | None:
    try:
        a, b = (t.strip() for t in str(testo).split("-")[:2])
        inizio = time(*(int(x) for x in a.split(":")[:2]))
        fine = time(*(int(x) for x in b.split(":")[:2]))
    except (TypeError, ValueError):
        return None
    return (inizio, fine) if fine > inizio else None


def _data(valore: Any) -> date | None:
    try:
        return date.fromisoformat(str((valore or {}).get("date", ""))[:10])
    except (AttributeError, ValueError):
        return None


def _periodo(h: dict[str, Any]) -> Periodo | None:
    dal, al = _data(h.get("from")), _data(h.get("to"))
    if dal is None or al is None:
        return None
    giorni = h.get("days") or []
    fasce: list[tuple[Fascia, ...]] = []
    for i in range(7):
        ore = giorni[i].get("hours") if i < len(giorni) and isinstance(giorni[i], dict) else []
        # Il sito a volte ripete la stessa fascia: si tolgono i doppioni.
        fasce.append(tuple(sorted({f for f in map(_fascia, ore or []) if f})))
    return Periodo(
        nome=str(h.get("description") or "Orario").strip(),
        descrizione=str(h.get("sub_description") or "").strip(),
        dal=dal,
        al=al,
        mensile=str(h.get("frequency") or "").upper() == "MONTHLY",
        fasce=tuple(fasce),
    )


def indirizzo(via: str, comune: str) -> str:
    parole = str(via or "").strip().lower().split()
    via = " ".join(p if i and p in _MINUSCOLE else p.capitalize() for i, p in enumerate(parole))
    return ", ".join(x for x in (via, comune) if x)


def trova_centro(dati: list[dict[str, Any]], comune: str, utenza: str = DEFAULT_UTENZA) -> Centro | None:
    """Il centro di raccolta che serve un comune, con gli orari per l'utenza scelta."""
    c = next((c for c in dati or [] if comune in (c.get("municipalityCodes") or [])), None)
    if c is None:
        return None
    orari = c.get("hours") or {}
    if not isinstance(orari, dict) or not orari:
        return None
    chiave = utenza if utenza in orari else "tutti" if "tutti" in orari else next(iter(orari))
    gruppo = orari[chiave] or {}
    periodi = tuple(p for p in map(_periodo, gruppo.get("hours") or []) if p)

    def _coord(v: Any) -> float | None:
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    return Centro(
        id=str(c.get("id")),
        nome=str(c.get("name") or "").strip(),
        indirizzo=indirizzo(c.get("address", ""), str(c.get("name") or "").strip()),
        latitudine=_coord(c.get("latitude")),
        longitudine=_coord(c.get("longitude")),
        comuni=tuple(str(m.get("name")) for m in c.get("municipalities") or [] if m.get("name")),
        utenza=str(gruppo.get("usedLabel") or chiave),
        periodi=periodi,
    )


def attributi(centro: Centro, adesso: datetime) -> dict[str, Any]:
    """Attributi comuni alle entità del centro di raccolta."""
    oggi = adesso.date()
    p = centro.periodo(oggi)
    in_corso = centro.in_corso(adesso)
    prossima = centro.prossima(adesso)
    attr: dict[str, Any] = {
        "centro": centro.nome,
        "indirizzo": centro.indirizzo,
        "utenza": centro.utenza,
        "periodo": p.etichetta if p else None,
        "oggi": testo_fasce(centro.fasce(oggi)) if p else None,
        "chiude_alle": in_corso[1].isoformat() if in_corso else None,
        "prossima_apertura": prossima[0].isoformat() if prossima else None,
        "orario": centro.orario(oggi),
        "comuni_serviti": list(centro.comuni),
    }
    if centro.solo_mensile(oggi):
        attr["nota"] = "Apertura mensile: i giorni esatti sono nel calendario del comune"
    if centro.latitudine is not None and centro.longitudine is not None:
        attr["latitude"] = centro.latitudine
        attr["longitude"] = centro.longitudine
    return attr

