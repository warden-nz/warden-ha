"""Warden DataUpdateCoordinators.

WardenCoordinator   — polls every 5 minutes for current price and spike status.
WardenForecastCoordinator — polls every 30 minutes for forecast and cheapest windows.

If the API returns 401 (token expired), both coordinators signal HA to show
the re-authentication flow.
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
    ENDPOINT_LATEST,
    ENDPOINT_STATUS,
    ENDPOINT_FORECAST,
    ENDPOINT_CHEAPEST,
)

_LOGGER = logging.getLogger(__name__)


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
    def _node(self) -> str:
        return self._entry.data[CONF_NODE]

    @property
    def _auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}"}

    async def _async_update_data(self) -> dict:
        """Fetch latest price + status. Called automatically every 5 minutes by HA."""
        try:
            prices = await self._get(ENDPOINT_LATEST)
            status = await self._get(ENDPOINT_STATUS)
        except ConfigEntryAuthFailed:
            raise
        except aiohttp.ClientConnectorError as err:
            raise UpdateFailed(f"Cannot reach api.wardenz.com: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Error fetching Warden data: {err}") from err

        node_data = next(
            (p for p in prices if p.get("node") == self._node), None
        )
        if node_data is None:
            raise UpdateFailed(
                f"Node {self._node} not found in API response. "
                "It may have changed on wardenz.com — try reloading the integration."
            )

        return {
            "node":            self._node,
            "price":           node_data.get("price"),
            "timestamp":       node_data.get("timestamp"),
            "alert_level":     status.get("alert_level", "normal"),
            "spike_active":    status.get("spike_active", False),
            "rolling_avg_30m": node_data.get("rolling_avg_30m"),
            "window_avg":      node_data.get("window_avg"),
            "window_p10":      node_data.get("window_p10"),
            "window_p90":      node_data.get("window_p90"),
            "window_samples":  node_data.get("window_samples"),
            "percentile":      node_data.get("percentile"),
        }

    async def _get(self, endpoint: str) -> dict | list:
        """GET a Warden API endpoint, raising ConfigEntryAuthFailed on 401."""
        async with self._session.get(
            f"{API_BASE_URL}{endpoint}",
            headers=self._auth_headers,
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status == 401:
                raise ConfigEntryAuthFailed(
                    "Warden token expired. Please re-enter your wardenz.com credentials."
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
    def _node(self) -> str:
        return self._entry.data[CONF_NODE]

    @property
    def _auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}"}

    async def _async_update_data(self) -> dict:
        """Fetch forecast prices and cheapest windows."""
        try:
            forecast = await self._get(ENDPOINT_FORECAST)
            cheapest = await self._get(ENDPOINT_CHEAPEST)
        except ConfigEntryAuthFailed:
            raise
        except aiohttp.ClientConnectorError as err:
            raise UpdateFailed(f"Cannot reach api.wardenz.com: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Error fetching Warden forecast data: {err}") from err

        # Index cheapest windows by duration for easy lookup in sensors
        cheapest_by_hours = {w["window_hours"]: w for w in cheapest}

        return {
            "node":             self._node,
            "forecast":         forecast,
            "next_price":       forecast[0]["price"] if forecast else None,
            "next_timestamp":   forecast[0]["trading_datetime"] if forecast else None,
            "forecast_node":    forecast[0]["node"] if forecast else None,
            "cheapest_1h":      cheapest_by_hours.get(1),
            "cheapest_2h":      cheapest_by_hours.get(2),
            "cheapest_3h":      cheapest_by_hours.get(3),
        }

    async def _get(self, endpoint: str) -> dict | list:
        """GET a Warden API endpoint, raising ConfigEntryAuthFailed on 401."""
        async with self._session.get(
            f"{API_BASE_URL}{endpoint}",
            headers=self._auth_headers,
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status == 401:
                raise ConfigEntryAuthFailed(
                    "Warden token expired. Please re-enter your wardenz.com credentials."
                )
            resp.raise_for_status()
            return await resp.json()