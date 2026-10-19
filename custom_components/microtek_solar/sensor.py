"""Sensor platform for Microtek Solar Inverter integration with offline night handling."""

from dataclasses import dataclass
import logging
import re
from typing import Any, Callable, Dict, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MicrotekDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


def _extract_number(val: Any) -> Optional[float]:
    """Parse numeric values from strings like '1465.6 W' or '6.7 kWh'."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    match = re.search(r"[-+]?\d*\.?\d+", str(val))
    if match:
        try:
            return float(match.group(0))
        except ValueError:
            return None
    return None


def _get_info_item(data: Dict[str, Any], key_name: str) -> Optional[str]:
    """Helper to extract an item from inverter.info list."""
    info_list = data.get("inverter", {}).get("info", [])
    for item in info_list:
        if item.get("key") == key_name:
            return item.get("value")
    return None


@dataclass
class MicrotekSensorEntityDescription(SensorEntityDescription):
    """Describes a Microtek solar sensor entity."""

    value_fn: Callable[[Dict[str, Any]], Any] = lambda x: None


SENSOR_TYPES: tuple[MicrotekSensorEntityDescription, ...] = (
    MicrotekSensorEntityDescription(
        key="current_power",
        name="Current Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:solar-power",
        value_fn=lambda data: _extract_number(_get_info_item(data, "currentPower")),
    ),
    MicrotekSensorEntityDescription(
        key="daily_production",
        name="Daily Production",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:calendar-today",
        value_fn=lambda data: _extract_number(_get_info_item(data, "yieldToday")),
    ),
    MicrotekSensorEntityDescription(
        key="total_production",
        name="Total Production",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:counter",
        value_fn=lambda data: _extract_number(_get_info_item(data, "totalYield")),
    ),
    MicrotekSensorEntityDescription(
        key="rated_power",
        name="Rated Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        icon="mdi:flash",
        value_fn=lambda data: _extract_number(_get_info_item(data, "ratedPower")),
    ),
    MicrotekSensorEntityDescription(
        key="alerts_count",
        name="Alert Count",
        icon="mdi:alert-circle-outline",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: _extract_number(_get_info_item(data, "alerts")),
    ),
    MicrotekSensorEntityDescription(
        key="wifi_signal",
        name="WiFi Signal Level",
        icon="mdi:wifi",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("device", {}).get("sta", {}).get("signal"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Microtek solar sensors."""
    coordinator: MicrotekDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        MicrotekSensor(coordinator, description, entry)
        for description in SENSOR_TYPES
    ]
    async_add_entities(entities)


class MicrotekSensor(
    CoordinatorEntity[MicrotekDataUpdateCoordinator], RestoreEntity, SensorEntity
):
    """Representation of a Microtek Solar Sensor with offline night preservation."""

    entity_description: MicrotekSensorEntityDescription

    def __init__(
        self,
        coordinator: MicrotekDataUpdateCoordinator,
        description: MicrotekSensorEntityDescription,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._entry = entry
        self._last_value: Any = None

        serial = str(entry.unique_id or entry.entry_id)
        inverter = coordinator.data.get("inverter", {}) if coordinator.data else {}
        sw_version = inverter.get("mainVersion", "8351-0116")

        self._attr_unique_id = f"{serial}_{description.key}"
        self._attr_name = f"Microtek Solar {description.name}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(serial))},
            name="Microtek Solar Inverter",
            manufacturer="Microtek / Deye OEM",
            model="MTK GTI 3kW D11",
            sw_version=sw_version,
            configuration_url=f"http://{entry.data.get('host', '192.168.1.x')}",
        )

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added, restoring previous state if available."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (None, "unknown", "unavailable"):
            try:
                self._last_value = float(last_state.state)
            except ValueError:
                self._last_value = last_state.state

    @property
    def available(self) -> bool:
        """Return True even when inverter is asleep/offline at night."""
        return True

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor. Realtime output shows 0 at night; yields retain last values."""
        is_online = (
            self.coordinator.data.get("online", True)
            if self.coordinator.data
            else False
        )

        # Real-time power output is explicitly 0 W when inverter is asleep/offline
        if self.entity_description.key == "current_power":
            if not is_online:
                return 0.0

        if self.coordinator.data:
            val = self.entity_description.value_fn(self.coordinator.data)
            if val is not None:
                self._last_value = val
                return val

        # Retain last known value for daily yields, lifetime yields, and rated power
        if self._last_value is not None:
            return self._last_value

        if self.entity_description.key == "current_power":
            return 0.0

        return None

    @property
    def icon(self) -> Optional[str]:
        """Return dynamic icon indicating online or night/offline state."""
        is_online = (
            self.coordinator.data.get("online", True)
            if self.coordinator.data
            else False
        )
        if not is_online:
            if self.entity_description.key == "current_power":
                return "mdi:weather-night"
            if self.entity_description.key in ("daily_production", "total_production"):
                return "mdi:solar-power-variant-outline"
            if self.entity_description.key == "wifi_signal":
                return "mdi:wifi-off"
        return self.entity_description.icon

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return device state attributes."""
        is_online = (
            self.coordinator.data.get("online", True)
            if self.coordinator.data
            else False
        )
        return {
            "device_status": "online" if is_online else "offline",
            "night_mode": not is_online,
        }
