"""Silea Raccolta Rifiuti: calendario della raccolta porta a porta di Silea (provincia di Lecco)."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import SileaCoordinator

PLATFORMS = [Platform.CALENDAR, Platform.SENSOR]

type SileaConfigEntry = ConfigEntry[SileaCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: SileaConfigEntry) -> bool:
    coordinator = SileaCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_options_changed))
    return True


async def _options_changed(hass: HomeAssistant, entry: SileaConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: SileaConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
