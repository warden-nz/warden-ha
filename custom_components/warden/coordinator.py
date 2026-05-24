"""Warden DataUpdateCoordinator.

Polls api.wardenz.com every 5 minutes for the latest price and spike
status for the user's configured node.

If the API returns 401 (token expired), it signals HA to show the
re-authentication flow rather than just logging an error.
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
    CONF_TOKEN,
    CONF_NODE,
    ENDPOINT_LATEST,
    ENDPOINT_STATUS,
)

_LOGGER = logging.getLogger(__name__)


class WardenCoordinator(DataUpdateCoordinator):
    """Shared data coordinator for all Warden entities."""

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
        """Always read the token from the live config entry so re-auth updates are picked up."""
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
            "window_avg_30d":  node_data.get("window_avg_30d"),
            "window_p10_30d":  node_data.get("window_p10_30d"),
            "window_p90_30d":  node_data.get("window_p90_30d"),
            "window_samples":  node_data.get("window_samples"),
            "percentile_30d":  node_data.get("percentile_30d"),
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
