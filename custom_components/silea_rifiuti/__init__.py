"""Silea Raccolta Rifiuti: calendario della raccolta porta a porta di Silea (provincia di Lecco)."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from .const import CARD_FILE, CARD_URL, DOMAIN
from .coordinator import CentriCoordinator, SileaCoordinator

PLATFORMS = [Platform.BINARY_SENSOR, Platform.CALENDAR, Platform.SENSOR]
CENTRI = "centri"
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type SileaConfigEntry = ConfigEntry[SileaCoordinator]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Serve la scheda per le dashboard e la carica in ogni pagina del frontend."""
    integration = await async_get_integration(hass, DOMAIN)
    path = Path(__file__).parent / "frontend" / CARD_FILE
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(path), True)]
    )
    add_extra_js_url(hass, f"{CARD_URL}?v={integration.version}")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: SileaConfigEntry) -> bool:
    coordinator = SileaCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    dati = hass.data.setdefault(DOMAIN, {})
    if CENTRI not in dati:
        dati[CENTRI] = CentriCoordinator(hass)
    coordinator.centri = dati[CENTRI]
    await coordinator.centri.primo_aggiornamento()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_options_changed))
    return True


async def _options_changed(hass: HomeAssistant, entry: SileaConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: SileaConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
