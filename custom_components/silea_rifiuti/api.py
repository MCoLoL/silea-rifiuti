"""Client per gli endpoint AJAX del calendario raccolta di sileaspa.it."""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

from .const import AJAX_URL, REFERER, USER_AGENT

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": REFERER,
}


class SileaError(Exception):
    """Errore di comunicazione con il sito Silea."""


class SileaApi:
    """Chiamate al sito: comuni, vie, mesi disponibili, calendario di un mese e centri di raccolta."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def _post(self, data: dict[str, str]) -> Any:
        try:
            async with asyncio.timeout(30):
                resp = await self._session.post(AJAX_URL, data=data, headers=HEADERS)
                resp.raise_for_status()
                return await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise SileaError(f"{data.get('action')}: {err}") from err

    async def comuni(self) -> list[dict[str, str]]:
        """Comuni serviti, come [{'id': 'A000', 'name': '...'}]."""
        res = await self._post({"action": "get_comuni"})
        return [{"id": c["id"], "name": c["name"]} for c in res or [] if c.get("id")]

    async def vie(self, comune: str) -> list[dict[str, str]]:
        """Vie di un comune."""
        res = await self._post({"action": "get_vie", "id_cliente": comune})
        return [{"id": v["id"], "name": v["name"]} for v in res or [] if v.get("id")]

    async def mesi(self, comune: str, via: str) -> list[str]:
        """Mesi pubblicati, come ['11_2026', '12_2026', ...]."""
        res = await self._post({"action": "get_months", "id_cliente": comune, "id_via": via})
        return [m["id"] for m in res or [] if m.get("id")]

    async def calendario(self, comune: str, via: str, mese: str) -> list[dict[str, Any]]:
        """Giorni di raccolta di un mese, nel formato restituito dal sito."""
        res = await self._post(
            {"action": "get_calendar", "id_cliente": comune, "id_via": via, "id_mese": mese}
        )
        return res if isinstance(res, list) else []

    async def centri(self) -> list[dict[str, Any]]:
        """Centri di raccolta con indirizzo, comuni serviti e orari, nel formato del sito."""
        res = await self._post({"action": "get_calendario_centri_raccolta_data"})
        return [c for c in res if isinstance(c, dict)] if isinstance(res, list) else []
