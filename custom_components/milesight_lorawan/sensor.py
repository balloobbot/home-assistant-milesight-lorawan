"""Milesight sensors."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, override

from homeassistant.components.lorawan import LoRaWANEntity
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfPressure,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import MilesightConfigEntry
from ._vendor.milesight_lorawan import TS201, MilesightDevice, UC51x
from .coordinator import MilesightCoordinator

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class MilesightSensorDescription[DeviceT: MilesightDevice](SensorEntityDescription):
    """Bind a supported model to one reported value."""

    device_types: tuple[type[DeviceT], ...]
    value_fn: Callable[[DeviceT], str | float | int | None]


def valve_state(device: UC51x, channel: int) -> str | None:
    """Return the reported valve state."""
    value = device.valve_1_open if channel == 1 else device.valve_2_open
    return None if value is None else "open" if value else "closed"


DESCRIPTIONS: tuple[MilesightSensorDescription[Any], ...] = (
    MilesightSensorDescription[TS201](
        key="temperature",
        device_types=(TS201,),
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.temperature,
    ),
    MilesightSensorDescription[MilesightDevice](
        key="battery",
        device_types=(TS201, UC51x),
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda device: (
            device.reported_battery_percent
            if device.reported_battery_percent is not None
            else device.battery_level
        ),
    ),
    MilesightSensorDescription[UC51x](
        key="valve_1",
        translation_key="valve_1",
        device_types=(UC51x,),
        device_class=SensorDeviceClass.ENUM,
        options=["open", "closed"],
        value_fn=lambda device: valve_state(device, 1),
    ),
    MilesightSensorDescription[UC51x](
        key="valve_2",
        translation_key="valve_2",
        device_types=(UC51x,),
        device_class=SensorDeviceClass.ENUM,
        options=["open", "closed"],
        value_fn=lambda device: valve_state(device, 2),
    ),
    MilesightSensorDescription[UC51x](
        key="pulse_count_1",
        translation_key="pulse_count_1",
        device_types=(UC51x,),
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda device: device.valve_1_pulse_count,
    ),
    MilesightSensorDescription[UC51x](
        key="pulse_count_2",
        translation_key="pulse_count_2",
        device_types=(UC51x,),
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda device: device.valve_2_pulse_count,
    ),
    MilesightSensorDescription[UC51x](
        key="pressure",
        device_types=(UC51x,),
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.KPA,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda device: device.pressure_kpa,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MilesightConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Milesight sensors."""

    @callback
    def added(coordinator: MilesightCoordinator) -> None:
        async_add_entities(
            MilesightSensor(coordinator, description)
            for description in DESCRIPTIONS
            if isinstance(coordinator.data, description.device_types)
        )

    entry.async_on_unload(entry.runtime_data.subscribe_coordinator_added(added))


class MilesightSensor(LoRaWANEntity[MilesightDevice], SensorEntity):
    """Represent a Milesight measurement."""

    coordinator: MilesightCoordinator
    entity_description: MilesightSensorDescription[Any]

    @property
    @override
    def device_info(self) -> DeviceInfo:
        return self.coordinator.device_info

    @property
    @override
    def native_value(self) -> str | float | int | None:
        return self.entity_description.value_fn(self.device)
