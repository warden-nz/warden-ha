"""Warden DataUpdateCoordinators.

WardenCoordinator        — polls every 5 minutes for current price and spike status.
WardenForecastCoordinator — polls every 30 minutes for forecast and cheapest windows.

If the API returns 401 (token expired), both coordinators signal HA to show
the re-authentication flow.

If the API returns 402 (free tier, upgrade required), both coordinators signal
HA to show the re-authentication flow with an upgrade message.

The /ha/* endpoints are gated at API_ACCESS_LEVEL (smart+ only). The account-
aware response returns data for the correct NZ node or AU NEM region based on
the JWT, so no client-side filtering is needed.
"""
from __future__ import annotations

import logging
from datetime import timedelta

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    API_BASE_URL,
    DEFAULT_SCAN_INTERVAL,
    FORECAST_SCAN_INTERVAL,
    CONF_TOKEN,
    CONF_NODE,
    CONF_COUNTRY,
    CONF_REGION,
)

_LOGGER = logging.getLogger(__name__)

# Dedicated HA endpoints — gated at API_ACCESS_LEVEL (smart+ only).
# Separate from the app/web endpoints so free-tier users retain app access.
HA_ENDPOINT_STATUS   = "/ha/status"
HA_ENDPOINT_FORECAST = "/ha/prices/forecast"
HA_ENDPOINT_CHEAPEST = "/ha/prices/cheapest"


class WardenCoordinator(DataUpdateCoordinator):
    """Shared data coordinator for current price entities."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._entry = entry
        self._session = async_get_clientsession(hass)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    @property
    def _token(self) -> str:
        return self._entry.data[CONF_TOKEN]

    @property
    def _node(self) -> str | None:
        return self._entry.data.get(CONF_NODE)

    @property
    def _country(self) -> str:
        return self._entry.data.get(CONF_COUNTRY, "NZ")

    @property
    def _region(self) -> str | None:
        return self._entry.data.get(CONF_REGION)

    @property
    def _location_label(self) -> str:
        """Human-readable label for this account's price location."""
        if self._country == "AU":
            return self._region or "unknown"
        return self._node or "unknown"

    @property
    def _auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}"}

    async def _async_update_data(self) -> dict:
        """Fetch current price + status from /ha/status.

        The endpoint is account-aware — it returns the correct node or region
        data based on the JWT, so no client-side filtering is required.
        Called automatically every 5 minutes by HA.
        """
        try:
            status = await self._get(HA_ENDPOINT_STATUS)
        except ConfigEntryAuthFailed:
            raise
        except aiohttp.ClientConnectorError as err:
            raise UpdateFailed(f"Cannot reach api.wardenz.com: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Error fetching Warden data: {err}") from err

        return {
            "node":            self._location_label,
            "price":           status.get("price"),
            "timestamp":       status.get("timestamp"),
            "alert_level":     status.get("alert_level", "normal"),
            "spike_active":    status.get("spike_active", False),
            "rolling_avg_30m": status.get("rolling_avg_30m"),
            "window_avg":      status.get("window_avg"),
            "window_p10":      status.get("window_p10"),
            "window_p90":      status.get("window_p90"),
            "window_samples":  status.get("window_samples"),
            "percentile":      status.get("percentile"),
            "carbon_intensity_gkwh": status.get("carbon_intensity_gkwh"),
            "renewable_pct":         status.get("renewable_pct"),
        }

    async def _get(self, endpoint: str) -> dict | list:
        """GET a Warden API endpoint.

        Raises ConfigEntryAuthFailed on 401 (token expired) or 402 (free tier
        — upgrade required). Both cause HA to show the re-authentication flow,
        which is the correct UX for either case.
        """
        async with self._session.get(
            f"{API_BASE_URL}{endpoint}",
            headers=self._auth_headers,
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status == 401:
                raise ConfigEntryAuthFailed(
                    "Warden token expired. Please re-enter your wardenz.com credentials."
                )
            if resp.status == 402:
                raise ConfigEntryAuthFailed(
                    "Warden Home Assistant integration requires a Smart or Device plan. "
                    "Upgrade at wardenz.com/upgrade."
                )
            resp.raise_for_status()
            return await resp.json()


class WardenForecastCoordinator(DataUpdateCoordinator):
    """Data coordinator for forecast and cheapest window entities.

    Polls every 30 minutes — forecast data doesn't change fast enough
    to justify more frequent updates.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._entry = entry
        self._session = async_get_clientsession(hass)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_forecast",
            update_interval=timedelta(seconds=FORECAST_SCAN_INTERVAL),
        )

    @property
    def _token(self) -> str:
        return self._entry.data[CONF_TOKEN]

    @property
    def _country(self) -> str:
        return self._entry.data.get(CONF_COUNTRY, "NZ")

    @property
    def _region(self) -> str | None:
        return self._entry.data.get(CONF_REGION)

    @property
    def _node(self) -> str | None:
        return self._entry.data.get(CONF_NODE)

    @property
    def _location_label(self) -> str:
        if self._country == "AU":
            return self._region or "unknown"
        return self._node or "unknown"

    @property
    def _auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}"}

    async def _async_update_data(self) -> dict:
        """Fetch forecast prices and cheapest windows."""
        try:
            forecast = await self._get(HA_ENDPOINT_FORECAST)
            cheapest = await self._get(HA_ENDPOINT_CHEAPEST)
        except ConfigEntryAuthFailed:
            raise
        except aiohttp.ClientConnectorError as err:
            raise UpdateFailed(f"Cannot reach api.wardenz.com: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Error fetching Warden forecast data: {err}") from err

        # Index cheapest windows by duration for easy lookup in sensors
        cheapest_by_hours = {w["window_hours"]: w for w in cheapest}

        return {
            "node":           self._location_label,
            "forecast":       forecast,
            "next_price":     forecast[0]["price"] if forecast else None,
            "next_timestamp": forecast[0]["trading_datetime"] if forecast else None,
            "cheapest_1h":    cheapest_by_hours.get(1),
            "cheapest_2h":    cheapest_by_hours.get(2),
            "cheapest_3h":    cheapest_by_hours.get(3),
        }

    async def _get(self, endpoint: str) -> dict | list:
        """GET a Warden API endpoint.

        Raises ConfigEntryAuthFailed on 401 (token expired) or 402 (free tier
        — upgrade required). Both cause HA to show the re-authentication flow,
        which is the correct UX for either case.
        """
        async with self._session.get(
            f"{API_BASE_URL}{endpoint}",
            headers=self._auth_headers,
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status == 401:
                raise ConfigEntryAuthFailed(
                    "Warden token expired. Please re-enter your wardenz.com credentials."
                )
            if resp.status == 402:
                raise ConfigEntryAuthFailed(
                    "Warden Home Assistant integration requires a Smart or Device plan. "
                    "Upgrade at wardenz.com/upgrade."
                )
            resp.raise_for_status()
            return await resp.json()