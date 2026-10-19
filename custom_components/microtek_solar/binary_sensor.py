"""Binary sensor platform for Microtek Solar Inverter integration with offline night handling."""

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MicrotekDataUpdateCoordinator


@dataclass
class MicrotekBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a Microtek binary sensor entity."""

    is_on_fn: Callable[[Dict[str, Any]], Optional[bool]] = lambda x: False


BINARY_SENSOR_TYPES: tuple[MicrotekBinarySensorEntityDescription, ...] = (
    MicrotekBinarySensorEntityDescription(
        key="inverter_online",
        name="Inverter Online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        icon="mdi:power",
        is_on_fn=lambda data: bool(data.get("online", False)),
    ),
    MicrotekBinarySensorEntityDescription(
        key="cloud_connected",
        name="Cloud Connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        icon="mdi:cloud-check",
        is_on_fn=lambda data: bool(
            data.get("online", False)
            and (
                data.get("cloud", [{}])[0].get("connect")
                if data.get("cloud")
                else False
            )
        ),
    ),
    MicrotekBinarySensorEntityDescription(
        key="fault_status",
        name="Fault Alert",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:alert-circle",
        is_on_fn=lambda data: bool(
            data.get("online", False)
            and any(
                item.get("key") == "alerts" and str(item.get("value", "0")) not in ("0", "")
                for item in data.get("inverter", {}).get("info", [])
            )
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Microtek solar binary sensors."""
    coordinator: MicrotekDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        MicrotekBinarySensor(coordinator, description, entry)
        for description in BINARY_SENSOR_TYPES
    ]
    async_add_entities(entities)


class MicrotekBinarySensor(
    CoordinatorEntity[MicrotekDataUpdateCoordinator], BinarySensorEntity
):
    """Representation of a Microtek Solar Binary Sensor."""

    entity_description: MicrotekBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: MicrotekDataUpdateCoordinator,
        description: MicrotekBinarySensorEntityDescription,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._entry = entry

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

    @property
    def available(self) -> bool:
        """Binary sensors remain available at night to show offline status instead of errors."""
        return True

    @property
    def is_on(self) -> Optional[bool]:
        """Return true if the binary sensor is on."""
        if not self.coordinator.data:
            return False
        return self.entity_description.is_on_fn(self.coordinator.data)

    @property
    def icon(self) -> Optional[str]:
        """Dynamic icons for online / offline status."""
        is_online = (
            self.coordinator.data.get("online", False)
            if self.coordinator.data
            else False
        )
        if self.entity_description.key == "inverter_online":
            return "mdi:power" if is_online else "mdi:power-sleep"
        if self.entity_description.key == "cloud_connected":
            return "mdi:cloud-check" if is_online else "mdi:cloud-off-outline"
        if self.entity_description.key == "fault_status":
            return "mdi:alert-circle" if self.is_on else "mdi:check-circle"
        return self.entity_description.icon
