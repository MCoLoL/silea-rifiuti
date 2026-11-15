"""Configurazione: si sceglie il comune e poi la via, dagli elenchi del sito Silea."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import SileaApi, SileaError
from .const import (
    CONF_COMUNE,
    CONF_COMUNE_NOME,
    CONF_MESI,
    CONF_VIA,
    CONF_VIA_NOME,
    DEFAULT_MESI,
    DOMAIN,
)


def _select(items: list[dict[str, str]]) -> SelectSelector:
    opts = [
        SelectOptionDict(value=i["id"], label=i["name"])
        for i in sorted(items, key=lambda i: i["name"].lower())
    ]
    return SelectSelector(SelectSelectorConfig(options=opts, mode=SelectSelectorMode.DROPDOWN))


class SileaConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._comuni: dict[str, str] = {}
        self._vie: dict[str, str] = {}
        self._comune: str | None = None

    def _api(self) -> SileaApi:
        return SileaApi(async_get_clientsession(self.hass))

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._comune = user_input[CONF_COMUNE]
            return await self.async_step_via()
        try:
            comuni = await self._api().comuni()
        except SileaError:
            return self.async_abort(reason="cannot_connect")
        if not comuni:
            return self.async_abort(reason="cannot_connect")
        self._comuni = {c["id"]: c["name"] for c in comuni}
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_COMUNE): _select(comuni)}),
            errors=errors,
        )

    async def async_step_via(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        assert self._comune is not None
        if user_input is not None:
            via = user_input[CONF_VIA]
            await self.async_set_unique_id(f"{self._comune}_{via}")
            self._abort_if_unique_id_configured()
            try:
                mesi = await self._api().mesi(self._comune, via)
            except SileaError:
                mesi = []
            if not mesi:
                errors["base"] = "no_calendar"
            else:
                comune_nome = self._comuni.get(self._comune, self._comune)
                via_nome = self._vie.get(via, via).title()
                return self.async_create_entry(
                    title=f"{via_nome}, {comune_nome}",
                    data={
                        CONF_COMUNE: self._comune,
                        CONF_COMUNE_NOME: comune_nome,
                        CONF_VIA: via,
                        CONF_VIA_NOME: via_nome,
                    },
                )
        if not self._vie:
            try:
                vie = await self._api().vie(self._comune)
            except SileaError:
                return self.async_abort(reason="cannot_connect")
            self._vie = {v["id"]: v["name"] for v in vie}
        vie_list = [{"id": k, "name": v} for k, v in self._vie.items()]
        return self.async_show_form(
            step_id="via",
            data_schema=vol.Schema({vol.Required(CONF_VIA): _select(vie_list)}),
            description_placeholders={"comune": self._comuni.get(self._comune, self._comune)},
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return SileaOptionsFlow()


class SileaOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data={CONF_MESI: int(user_input[CONF_MESI])})
        attuale = self.config_entry.options.get(CONF_MESI, DEFAULT_MESI)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MESI, default=attuale): NumberSelector(
                        NumberSelectorConfig(min=1, max=12, step=1, mode=NumberSelectorMode.BOX)
                    )
                }
            ),
        )
