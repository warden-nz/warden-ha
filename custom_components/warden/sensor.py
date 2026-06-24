"""Warden price sensors."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CHEAPEST_WINDOW_HOURS, CONF_COUNTRY, CONF_REGION, CONF_NODE
from .coordinator import WardenCoordinator, WardenForecastCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: WardenCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    forecast_coordinator: WardenForecastCoordinator = hass.data[DOMAIN][entry.entry_id]["forecast_coordinator"]

    entities = [
        WardenPriceSensor(coordinator, entry),
        WardenAlertLevelSensor(coordinator, entry),
        WardenRollingAvg30mSensor(coordinator, entry),
        WardenWindowAvgSensor(coordinator, entry),
        WardenPercentileSensor(coordinator, entry),
        WardenCarbonIntensitySensor(coordinator, entry),
        WardenRenewablePctSensor(coordinator, entry),
        WardenForecastSensor(forecast_coordinator, entry),
        *[WardenCheapestWindowSensor(forecast_coordinator, entry, hours)
          for hours in CHEAPEST_WINDOW_HOURS],
    ]
    async_add_entities(entities)


def _location_label(entry: ConfigEntry) -> str:
    """Return node for NZ users, region for AU users."""
    if entry.data.get(CONF_COUNTRY) == "AU":
        return entry.data.get(CONF_REGION) or "unknown"
    return entry.data.get(CONF_NODE) or "unknown"


def _device_info(entry: ConfigEntry, node: str) -> DeviceInfo:
    country = entry.data.get(CONF_COUNTRY, "NZ")
    model = "AU Electricity Price Monitor" if country == "AU" else "NZ Electricity Price Monitor"
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=f"Warden ({node})",
        manufacturer="Warden",
        model=model,
        configuration_url="https://wardenz.com",
    )


# ---------------------------------------------------------------------------
# Current price sensors
# ---------------------------------------------------------------------------

class WardenPriceSensor(CoordinatorEntity, SensorEntity):
    """Current spot price in $/kWh for the account's node or region."""

    _attr_native_unit_of_measurement = "$/kWh"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:lightning-bolt"

    def __init__(self, coordinator: WardenCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        node = _location_label(entry)
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
        node = _location_label(entry)
        self._attr_unique_id = f"{entry.entry_id}_alert_level"
        self._attr_name = f"Warden {node} Alert Level"

    @property
    def device_info(self) -> DeviceInfo:
        return _device_info(self._entry, self.coordinator.data.get("node", ""))

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("alert_level")


class WardenRollingAvg30mSensor(CoordinatorEntity, SensorEntity):
    """Rolling average price over the last 30 minutes in $/kWh."""

    _attr_native_unit_of_measurement = "$/kWh"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:chart-bell-curve"

    def __init__(self, coordinator: WardenCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        node = _location_label(entry)
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
        return {"node": self.coordinator.data.get("node")}


class WardenWindowAvgSensor(CoordinatorEntity, SensorEntity):
    """Historical average price for this 30-minute window in $/kWh."""

    _attr_native_unit_of_measurement = "$/kWh"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:chart-timeline-variant"

    def __init__(self, coordinator: WardenCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        node = _location_label(entry)
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
        node = _location_label(entry)
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


class WardenCarbonIntensitySensor(CoordinatorEntity, SensorEntity):
    """Current grid carbon intensity in g CO2/kWh.

    NZ only — em6's free carbon intensity feed is a single nationwide
    figure with no per-node or per-region breakdown, so this value is
    the same for every NZ user regardless of node or tier. Returns
    unavailable for AU accounts until an AU emissions source is added.
    """

    _attr_native_unit_of_measurement = "g/kWh"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:molecule-co2"

    def __init__(self, coordinator: WardenCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        node = _location_label(entry)
        self._attr_unique_id = f"{entry.entry_id}_carbon_intensity"
        self._attr_name = f"Warden {node} Carbon Intensity"

    @property
    def device_info(self) -> DeviceInfo:
        return _device_info(self._entry, self.coordinator.data.get("node", ""))

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.get("carbon_intensity_gkwh")

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "node":  self.coordinator.data.get("node"),
            "scope": "NZ-wide (em6) — not specific to this node",
        }


class WardenRenewablePctSensor(CoordinatorEntity, SensorEntity):
    """Current percentage of NZ generation that is renewable.

    NZ only — see WardenCarbonIntensitySensor for the same nationwide-only
    caveat. Returns unavailable for AU accounts until an AU emissions
    source is added.
    """

    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:leaf"

    def __init__(self, coordinator: WardenCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        node = _location_label(entry)
        self._attr_unique_id = f"{entry.entry_id}_renewable_pct"
        self._attr_name = f"Warden {node} Renewable %"

    @property
    def device_info(self) -> DeviceInfo:
        return _device_info(self._entry, self.coordinator.data.get("node", ""))

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.get("renewable_pct")

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "node":  self.coordinator.data.get("node"),
            "scope": "NZ-wide (em6) — not specific to this node",
        }


# ---------------------------------------------------------------------------
# Forecast sensors
# ---------------------------------------------------------------------------

class WardenForecastSensor(CoordinatorEntity, SensorEntity):
    """Next period's forecast price in $/kWh, with full 24hr forecast as attributes."""

    _attr_native_unit_of_measurement = "$/kWh"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:chart-timeline"

    def __init__(
        self, coordinator: WardenForecastCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        node = _location_label(entry)
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
            "node":           self.coordinator.data.get("node"),
            "next_timestamp": self.coordinator.data.get("next_timestamp"),
            "period_count":   len(forecast),
            "prices":         forecast,
        }


class WardenCheapestWindowSensor(CoordinatorEntity, SensorEntity):
    """Cheapest upcoming contiguous window of N hours in $/kWh."""

    _attr_native_unit_of_measurement = "$/kWh"
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
        self._attr_unique_id = f"{entry.entry_id}_cheapest_{window_hours}h"
        self._attr_name = f"Warden Cheapest {window_hours}h Window"

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