"""Warden NZ Electricity — Home Assistant integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import WardenCoordinator, WardenForecastCoordinator

PLATFORMS = ["sensor", "binary_sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Called by HA when the integration is loaded (on startup or after setup)."""
    coordinator = WardenCoordinator(hass, entry)
    forecast_coordinator = WardenForecastCoordinator(hass, entry)

    # First poll immediately so entities have data right away
    await coordinator.async_config_entry_first_refresh()
    await forecast_coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator":          coordinator,
        "forecast_coordinator": forecast_coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Called when the user removes the integration."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok