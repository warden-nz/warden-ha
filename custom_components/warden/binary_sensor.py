"""Warden spike binary sensor."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WardenCoordinator
from .sensor import _device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: WardenCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([WardenSpikeSensor(coordinator, entry)])


class WardenSpikeSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor: ON when a price spike is active.

    Use this as the trigger in automations:
      ON  → pause EV charging, switch battery to export mode
      OFF → resume normal schedule
    """

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:transmission-tower-export"

    def __init__(self, coordinator: WardenCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        node = entry.data.get("node", "unknown")
        self._attr_unique_id = f"{entry.entry_id}_spike_active"
        self._attr_name = f"Warden {node} Spike Active"

    @property
    def device_info(self) -> DeviceInfo:
        return _device_info(self._entry, self.coordinator.data.get("node", ""))

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("spike_active", False))

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "alert_level": self.coordinator.data.get("alert_level"),
            "node":        self.coordinator.data.get("node"),
            "price":       self.coordinator.data.get("price"),
        }