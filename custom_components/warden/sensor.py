"""Warden price sensors."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WardenCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: WardenCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        WardenPriceSensor(coordinator, entry),
        WardenAlertLevelSensor(coordinator, entry),
        WardenRollingAvg30mSensor(coordinator, entry),
        WardenWindowAvgSensor(coordinator, entry),
        WardenPercentileSensor(coordinator, entry),
    ])


def _device_info(entry: ConfigEntry, node: str) -> DeviceInfo:
    """Shared device info so all entities appear under one device in HA."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=f"Warden ({node})",
        manufacturer="Warden",
        model="NZ Electricity Price Monitor",
        configuration_url="https://wardenz.com",
    )


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
    """Historical average price for this 30-minute window (same time, same day of week).

    Improves over time as more data accumulates — after a year you have
    52 data points per window slot, after 10 years, 500.
    """

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
    """Where the current price sits in the historical distribution for this time window.

    A value of 20 means the price is cheaper than 80% of all historical prices
    for this same 30-minute window — i.e. it's cheap.
    A value of 90 means it's more expensive than 90% of historical prices — i.e. it's a spike.

    Accuracy improves over time as more data accumulates.
    """

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