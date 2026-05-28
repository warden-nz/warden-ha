"""Warden price sensors."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CHEAPEST_WINDOW_HOURS
from .coordinator import WardenCoordinator, WardenForecastCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: WardenCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    forecast_coordinator: WardenForecastCoordinator = hass.data[DOMAIN][entry.entry_id]["forecast_coordinator"]

    entities = [
        # Current price sensors
        WardenPriceSensor(coordinator, entry),
        WardenAlertLevelSensor(coordinator, entry),
        WardenRollingAvg30mSensor(coordinator, entry),
        WardenWindowAvgSensor(coordinator, entry),
        WardenPercentileSensor(coordinator, entry),
        # Forecast sensor
        WardenForecastSensor(forecast_coordinator, entry),
        # Cheapest window sensors
        *[WardenCheapestWindowSensor(forecast_coordinator, entry, hours)
          for hours in CHEAPEST_WINDOW_HOURS],
    ]
    async_add_entities(entities)


def _device_info(entry: ConfigEntry, node: str) -> DeviceInfo:
    """Shared device info so all entities appear under one device in HA."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=f"Warden ({node})",
        manufacturer="Warden",
        model="NZ Electricity Price Monitor",
        configuration_url="https://wardenz.com",
    )


# ---------------------------------------------------------------------------
# Current price sensors (unchanged)
# ---------------------------------------------------------------------------

class WardenPriceSensor(CoordinatorEntity, SensorEntity):
    """Current spot price in NZD/MWh for the account's node."""

    _attr_native_unit_of_measurement = "NZD/MWh"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:lightning-bolt"

    def __init__(self, coordinator: WardenCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        node = entry.data.get("node", "unknown")
        self._attr_unique_id = f"{entry.entry_id}_price"
        self._attr_name = f"Warden {node} Price"

    @property
    def device_info(self) -> DeviceInfo:
        return _device_info(self._entry, self.coordinator.data.get("node", ""))

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.get("price")

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "node":         self.coordinator.data.get("node"),
            "last_updated": self.coordinator.data.get("timestamp"),
            "alert_level":  self.coordinator.data.get("alert_level"),
        }


class WardenAlertLevelSensor(CoordinatorEntity, SensorEntity):
    """Text sensor: 'normal', 'high', or 'spike'."""

    _attr_icon = "mdi:alert-circle-outline"

    def __init__(self, coordinator: WardenCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        node = entry.data.get("node", "unknown")
        self._attr_unique_id = f"{entry.entry_id}_alert_level"
        self._attr_name = f"Warden {node} Alert Level"

    @property
    def device_info(self) -> DeviceInfo:
        return _device_info(self._entry, self.coordinator.data.get("node", ""))

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("alert_level")


class WardenRollingAvg30mSensor(CoordinatorEntity, SensorEntity):
    """Rolling average price over the last 30 minutes."""

    _attr_native_unit_of_measurement = "NZD/MWh"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:chart-bell-curve"

    def __init__(self, coordinator: WardenCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        node = entry.data.get("node", "unknown")
        self._attr_unique_id = f"{entry.entry_id}_rolling_avg_30m"
        self._attr_name = f"Warden {node} 30m Average"

    @property
    def device_info(self) -> DeviceInfo:
        return _device_info(self._entry, self.coordinator.data.get("node", ""))

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.get("rolling_avg_30m")

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "node": self.coordinator.data.get("node"),
        }


class WardenWindowAvgSensor(CoordinatorEntity, SensorEntity):
    """Historical average price for this 30-minute window (same time, same day of week)."""

    _attr_native_unit_of_measurement = "NZD/MWh"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:chart-timeline-variant"

    def __init__(self, coordinator: WardenCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        node = entry.data.get("node", "unknown")
        self._attr_unique_id = f"{entry.entry_id}_window_avg"
        self._attr_name = f"Warden {node} Window Average"

    @property
    def device_info(self) -> DeviceInfo:
        return _device_info(self._entry, self.coordinator.data.get("node", ""))

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.get("window_avg")

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "node":           self.coordinator.data.get("node"),
            "window_p10":     self.coordinator.data.get("window_p10"),
            "window_p90":     self.coordinator.data.get("window_p90"),
            "window_samples": self.coordinator.data.get("window_samples"),
        }


class WardenPercentileSensor(CoordinatorEntity, SensorEntity):
    """Where the current price sits in the historical distribution for this time window."""

    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:percent"

    def __init__(self, coordinator: WardenCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        node = entry.data.get("node", "unknown")
        self._attr_unique_id = f"{entry.entry_id}_percentile"
        self._attr_name = f"Warden {node} Price Percentile"

    @property
    def device_info(self) -> DeviceInfo:
        return _device_info(self._entry, self.coordinator.data.get("node", ""))

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.get("percentile")

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "node":           self.coordinator.data.get("node"),
            "window_samples": self.coordinator.data.get("window_samples"),
            "interpretation": self._interpret(),
        }

    def _interpret(self) -> str | None:
        pct = self.coordinator.data.get("percentile")
        if pct is None:
            return None
        if pct <= 10:
            return "very cheap"
        if pct <= 30:
            return "cheap"
        if pct <= 70:
            return "normal"
        if pct <= 90:
            return "expensive"
        return "spike"


# ---------------------------------------------------------------------------
# Forecast sensors
# ---------------------------------------------------------------------------

class WardenForecastSensor(CoordinatorEntity, SensorEntity):
    """Next period's forecast price, with the full 24hr forecast as attributes.

    State: the price of the next 5-minute period.
    Attributes: full forecast array for use in HA templates and automations.

    Example template to get the price in 2 hours:
        {{ state_attr('sensor.warden_otа2201_forecast', 'prices')[24]['price'] }}
    """

    _attr_native_unit_of_measurement = "NZD/MWh"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:chart-timeline"

    def __init__(
        self, coordinator: WardenForecastCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        node = entry.data.get("node", "unknown")
        self._attr_unique_id = f"{entry.entry_id}_forecast"
        self._attr_name = f"Warden {node} Forecast"

    @property
    def device_info(self) -> DeviceInfo:
        return _device_info(self._entry, self.coordinator.data.get("node", ""))

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.get("next_price")

    @property
    def extra_state_attributes(self) -> dict:
        forecast = self.coordinator.data.get("forecast", [])
        return {
            "node":           self.coordinator.data.get("forecast_node"),
            "next_timestamp": self.coordinator.data.get("next_timestamp"),
            "period_count":   len(forecast),
            "prices":         forecast,
        }


class WardenCheapestWindowSensor(CoordinatorEntity, SensorEntity):
    """Cheapest upcoming contiguous window of N hours.

    State: average $/MWh across the cheapest window.
    Attributes: start_time and end_time of that window.

    Example automation trigger — start dishwasher at cheapest 1hr window:
        trigger:
          platform: template
          value_template: >
            {{ now().isoformat() >= state_attr('sensor.warden_oта2201_cheapest_1h', 'start_time') }}
    """

    _attr_native_unit_of_measurement = "NZD/MWh"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:clock-check-outline"

    def __init__(
        self,
        coordinator: WardenForecastCoordinator,
        entry: ConfigEntry,
        window_hours: int,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._window_hours = window_hours
        node = entry.data.get("node", "unknown")
        self._attr_unique_id = f"{entry.entry_id}_cheapest_{window_hours}h"
        self._attr_name = f"Warden {node} Cheapest {window_hours}h Window"

    @property
    def device_info(self) -> DeviceInfo:
        return _device_info(self._entry, self.coordinator.data.get("node", ""))

    @property
    def _window_data(self) -> dict | None:
        return self.coordinator.data.get(f"cheapest_{self._window_hours}h")

    @property
    def native_value(self) -> float | None:
        w = self._window_data
        return w["avg_price"] if w else None

    @property
    def extra_state_attributes(self) -> dict:
        w = self._window_data
        if not w:
            return {"node": self.coordinator.data.get("node")}
        return {
            "node":         w.get("node"),
            "start_time":   w.get("start_time"),
            "end_time":     w.get("end_time"),
            "window_hours": self._window_hours,
        }